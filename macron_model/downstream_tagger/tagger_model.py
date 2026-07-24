'''
Char-level tagger: same backbone shape as macron_model/model.py (factored
letter/diacritic plane embeddings + positional embedding -> TransformerEncoder),
plus an optional third "macron" plane, plus mean-pooling of char hidden states
into per-token representations, plus two classification heads (XPOS, lemma
edit-script). The macron plane is the only architectural difference between the
"with macronization" and "without" ablation arms -- everything else (layer count,
hidden size, heads, training budget) is identical, controlled via
config.use_macron_plane.
'''

import sys

import torch
from torch import nn
from transformers import PretrainedConfig, PreTrainedModel

sys.path.insert(0, "..")  # macron_model/ for tokenizer.py
from tokenizer import PLANE1_VOCAB_SIZE, LABEL_IGNORE_INDEX  # noqa: E402

MACRON_PLANE_VOCAB_SIZE = 3  # none / short / long


class TaggerConfig(PretrainedConfig):
    model_type = "grc-tagger-char"

    def __init__(
        self,
        plane1_vocab_size=PLANE1_VOCAB_SIZE,
        plane2_vocab_size=64,
        use_macron_plane=False,
        num_xpos_labels=2,
        num_lemma_labels=2,
        hidden_size=128,
        num_hidden_layers=4,
        num_attention_heads=4,
        intermediate_size=512,
        max_position_embeddings=512,
        dropout=0.1,
        pad_token_id=0,
        **kwargs,
    ):
        super().__init__(pad_token_id=pad_token_id, **kwargs)
        self.plane1_vocab_size = plane1_vocab_size
        self.plane2_vocab_size = plane2_vocab_size
        self.use_macron_plane = use_macron_plane
        self.num_xpos_labels = num_xpos_labels
        self.num_lemma_labels = num_lemma_labels
        self.hidden_size = hidden_size
        self.num_hidden_layers = num_hidden_layers
        self.num_attention_heads = num_attention_heads
        self.intermediate_size = intermediate_size
        self.max_position_embeddings = max_position_embeddings
        self.dropout = dropout


class TaggerModel(PreTrainedModel):
    config_class = TaggerConfig
    base_model_prefix = "tagger"
    main_input_name = "plane1_ids"

    def __init__(self, config):
        super().__init__(config)
        h = config.hidden_size

        self.plane1_embed = nn.Embedding(config.plane1_vocab_size, h, padding_idx=config.pad_token_id)
        self.plane2_embed = nn.Embedding(config.plane2_vocab_size, h, padding_idx=config.pad_token_id)
        self.plane3_embed = (
            nn.Embedding(MACRON_PLANE_VOCAB_SIZE, h) if config.use_macron_plane else None
        )
        self.position_embed = nn.Embedding(config.max_position_embeddings, h)

        self.embed_layernorm = nn.LayerNorm(h)
        self.embed_dropout = nn.Dropout(config.dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=h,
            nhead=config.num_attention_heads,
            dim_feedforward=config.intermediate_size,
            dropout=config.dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=config.num_hidden_layers)

        self.pool_dropout = nn.Dropout(config.dropout)
        self.xpos_classifier = nn.Linear(h, config.num_xpos_labels)
        self.lemma_classifier = nn.Linear(h, config.num_lemma_labels)

        self.post_init()

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            module.weight.data.normal_(mean=0.0, std=0.02)
            if module.bias is not None:
                module.bias.data.zero_()
        elif isinstance(module, nn.Embedding):
            module.weight.data.normal_(mean=0.0, std=0.02)
            if module.padding_idx is not None:
                module.weight.data[module.padding_idx].zero_()
        elif isinstance(module, nn.LayerNorm):
            module.bias.data.zero_()
            module.weight.data.fill_(1.0)

    def _pool_tokens(self, hidden, token_id_per_char, num_tokens):
        '''Mean-pool char hidden states into per-token vectors.
        token_id_per_char: (B, L) in [0, num_tokens] -- num_tokens itself is the
        trash bucket for separator/padding chars that belong to no token.'''
        bsz, seq_len, h = hidden.shape
        buckets = num_tokens + 1
        index = token_id_per_char.unsqueeze(-1).expand(-1, -1, h)

        pooled = hidden.new_zeros(bsz, buckets, h)
        pooled.scatter_add_(1, index, hidden)

        counts = hidden.new_zeros(bsz, buckets)
        counts.scatter_add_(1, token_id_per_char, torch.ones_like(token_id_per_char, dtype=hidden.dtype))

        pooled = pooled / counts.clamp(min=1).unsqueeze(-1)
        return pooled[:, :num_tokens, :]

    def forward(
        self,
        plane1_ids,
        plane2_ids,
        token_id_per_char,
        plane3_ids=None,
        attention_mask=None,
        num_tokens=None,
        xpos_labels=None,
        lemma_labels=None,
        **kwargs,
    ):
        bsz, seq_len = plane1_ids.shape
        device = plane1_ids.device

        positions = torch.arange(seq_len, device=device).unsqueeze(0).expand(bsz, seq_len)
        hidden = self.plane1_embed(plane1_ids) + self.plane2_embed(plane2_ids) + self.position_embed(positions)
        if self.plane3_embed is not None:
            if plane3_ids is None:
                raise ValueError("use_macron_plane=True but no plane3_ids given")
            hidden = hidden + self.plane3_embed(plane3_ids)
        hidden = self.embed_dropout(self.embed_layernorm(hidden))

        key_padding_mask = None
        if attention_mask is not None:
            key_padding_mask = attention_mask == 0

        hidden = self.encoder(hidden, src_key_padding_mask=key_padding_mask)

        num_tokens = num_tokens if num_tokens is not None else int(token_id_per_char.max().item())
        pooled = self.pool_dropout(self._pool_tokens(hidden, token_id_per_char, num_tokens))

        xpos_logits = self.xpos_classifier(pooled)
        lemma_logits = self.lemma_classifier(pooled)

        loss = None
        if xpos_labels is not None and lemma_labels is not None:
            loss_fct = nn.CrossEntropyLoss(ignore_index=LABEL_IGNORE_INDEX)
            xpos_loss = loss_fct(xpos_logits.reshape(-1, self.config.num_xpos_labels), xpos_labels.reshape(-1))
            lemma_loss = loss_fct(lemma_logits.reshape(-1, self.config.num_lemma_labels), lemma_labels.reshape(-1))
            loss = xpos_loss + lemma_loss

        return {
            "loss": loss,
            "xpos_logits": xpos_logits,
            "lemma_logits": lemma_logits,
        }

    def num_parameters_readable(self):
        n = sum(p.numel() for p in self.parameters())
        return f"{n / 1e6:.2f}M"


if __name__ == "__main__":
    cfg = TaggerConfig(plane2_vocab_size=20, use_macron_plane=True, num_xpos_labels=300, num_lemma_labels=2000)
    model = TaggerModel(cfg)
    print(model.num_parameters_readable(), "parameters (with macron plane)")

    B, L, T = 2, 12, 4
    plane1 = torch.randint(0, cfg.plane1_vocab_size, (B, L))
    plane2 = torch.randint(0, cfg.plane2_vocab_size, (B, L))
    plane3 = torch.randint(0, 3, (B, L))
    token_id_per_char = torch.randint(0, T, (B, L))
    xpos_labels = torch.randint(0, cfg.num_xpos_labels, (B, T))
    lemma_labels = torch.randint(0, cfg.num_lemma_labels, (B, T))

    out = model(
        plane1_ids=plane1, plane2_ids=plane2, plane3_ids=plane3,
        token_id_per_char=token_id_per_char, num_tokens=T,
        xpos_labels=xpos_labels, lemma_labels=lemma_labels,
    )
    print("loss:", out["loss"].item())
    print("xpos_logits shape:", out["xpos_logits"].shape)
    print("lemma_logits shape:", out["lemma_logits"].shape)
