# TO-DO

- find all wiktionary titles to scrape
- GPT4o for morphology


macronizer workflow
1) apply rules of accentuation
2) if the line of the word is scanned in hypotactic, check that
3) check "hardcoded" database
4) if not in db:
   1) get morphemes from GPT API
   2) apply algorithmic morph rules
   3) if still undecided, send to GPT

NB
- Marking of superheavies is in general irreducibly conjectural: wiktionaries decisions are often scientifically unfounded.


Example: ἵσταμαι ^ (present), ἵσταμαι - (imperfect)

```mermaid
graph TD
    classDef commentStyle fill:transparent,stroke:none,font-size:12px,font-style:italic;
    classDef successStyle fill:#8FBC8F,stroke:#006400,stroke-width:2px;
    classDef failStyle fill:#F08080,stroke:#8B0000,stroke-width:2px;
    classDef formStyle fill:#FFFFE0,stroke:#FFD700,stroke-width:2px;
    linkStyle default stroke-width:3px;

    TLG[Sentence with dichrona in TLG] --> OdyCy
    OdyCy --> Word
    Word --> Dichrona{Dichrona?}
    Dichrona -->|Yes| WordDichrona
    Dichrona -->|No| NextWord[Move to next word]
    NextWord --> Word
    Meter((Optional: Meter)) -.-> WordDichrona[Word with dichrona]:::formStyle
    WordDichrona --> Decision{Word in db?}
    Decision -->|Yes, exactly 1 match| Success[Macronize!]:::successStyle
    Decision -->|Yes, but > 1 matches differing w.r.t. macrons| MorphSelector{Compare OdyCy analysis with db forms}
    Decision -->|No| MorphBoundaries[Mark morpheme boundaries with ChatGPT API]
    MorphBoundaries --> DecisionPrefixes{Prefixes that can be removed?}
    DecisionPrefixes -->|Yes, extract subform| Word
    DecisionPrefixes -->|No| Fail[Algorithm exhausted]:::failStyle
    Fail --> Placeholder[Temporary suggestion from ChatGPT API]
    Placeholder --> Manual[Manual proof-checking]
    MorphSelector -->|Clear match| Success[Macronize!]:::successStyle
    MorphSelector --> Fail:::failStyle
    Success --> MetricCheck[Optional proto-metrical check]
    MetricCheck["[Proto-metrical check]"] --> DecisionMeter{Dichronon in first or penultimate syllable of a hexameter line?}
    DecisionMeter -->|Yes| Overwrite[Overwrite macron]:::successStyle
    DecisionMeter -->|No| Keep[Keep macrons as is]
```
