'''
A small char-level transformer that tags each character position with a macron class
(none / short / long). Input is two factored embedding "planes" per position -- the base
letter (25 = 24 Greek letters + space, plus an <other>/<pad> bucket) and the diacritic
combination on that letter -- summed with a learned positional embedding. This is a plain
transformers.PreTrainedModel/PretrainedConfig subclass so it saves/loads/push_to_hub's like
any other HF model.
'''

import math

import torch
from torch import nn
from transformers import PretrainedConfig, PreTrainedModel
from transformers.modeling_outputs import TokenClassifierOutput

from tokenizer import PLANE1_VOCAB_SIZE, LABEL_IGNORE_INDEX


class MacronizerConfig(PretrainedConfig):
    model_type = "grc-macronizer-char"

    def __init__(
        self,
        plane1_vocab_size=PLANE1_VOCAB_SIZE,
        plane2_vocab_size=64,
        hidden_size=128,
        num_hidden_layers=4,
        num_attention_heads=4,
        intermediate_size=512,
        max_position_embeddings=512,
        dropout=0.1,
        num_labels=3,
        pad_token_id=0,
        **kwargs,
    ):
        super().__init__(pad_token_id=pad_token_id, **kwargs)
        self.plane1_vocab_size = plane1_vocab_size
        self.plane2_vocab_size = plane2_vocab_size
        self.hidden_size = hidden_size
        self.num_hidden_layers = num_hidden_layers
        self.num_attention_heads = num_attention_heads
        self.intermediate_size = intermediate_size
        self.max_position_embeddings = max_position_embeddings
        self.dropout = dropout
        self.num_labels = num_labels


class MacronizerModel(PreTrainedModel):
    config_class = MacronizerConfig
    base_model_prefix = "macronizer"
    main_input_name = "plane1_ids"

    def __init__(self, config):
        super().__init__(config)
        h = config.hidden_size

        self.plane1_embed = nn.Embedding(config.plane1_vocab_size, h, padding_idx=config.pad_token_id)
        self.plane2_embed = nn.Embedding(config.plane2_vocab_size, h, padding_idx=config.pad_token_id)
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

        self.classifier_dropout = nn.Dropout(config.dropout)
        self.classifier = nn.Linear(h, config.num_labels)

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

    def forward(
        self,
        plane1_ids,
        plane2_ids,
        attention_mask=None,
        labels=None,
        **kwargs,
    ):
        bsz, seq_len = plane1_ids.shape
        device = plane1_ids.device

        positions = torch.arange(seq_len, device=device).unsqueeze(0).expand(bsz, seq_len)
        hidden = self.plane1_embed(plane1_ids) + self.plane2_embed(plane2_ids) + self.position_embed(positions)
        hidden = self.embed_dropout(self.embed_layernorm(hidden))

        key_padding_mask = None
        if attention_mask is not None:
            key_padding_mask = attention_mask == 0  # True where padded, per nn.Transformer convention

        hidden = self.encoder(hidden, src_key_padding_mask=key_padding_mask)
        logits = self.classifier(self.classifier_dropout(hidden))

        loss = None
        if labels is not None:
            loss_fct = nn.CrossEntropyLoss(ignore_index=LABEL_IGNORE_INDEX)
            loss = loss_fct(logits.view(-1, self.config.num_labels), labels.view(-1))

        return TokenClassifierOutput(loss=loss, logits=logits, hidden_states=None, attentions=None)

    def num_parameters_readable(self):
        n = sum(p.numel() for p in self.parameters())
        return f"{n / 1e6:.2f}M"


if __name__ == "__main__":
    cfg = MacronizerConfig(plane2_vocab_size=20)
    model = MacronizerModel(cfg)
    print(model.num_parameters_readable(), "parameters")

    plane1 = torch.randint(0, cfg.plane1_vocab_size, (2, 10))
    plane2 = torch.randint(0, cfg.plane2_vocab_size, (2, 10))
    labels = torch.randint(0, 3, (2, 10))
    labels[:, :3] = LABEL_IGNORE_INDEX

    out = model(plane1_ids=plane1, plane2_ids=plane2, labels=labels)
    print("loss:", out.loss.item())
    print("logits shape:", out.logits.shape)
