# test_senegal_normalizer.py
# Test examples to verify the normalizer works correctly

from transformers import WhisperTokenizer

# Initialize tokenizer with Senegal normalizer
tokenizer = WhisperTokenizer.from_pretrained(
    "openai/whisper-base",
    use_senegal_normalizer=True
)

# Test cases
test_cases = [
    # Service codes
    ("tapez dièse deux cent cinq dièse", "#205#"),
    ("composer étoile huit cent quatre-vingt-huit étoile", "*888*"),
    ("dièse deux cent cinquante dièse", "#250#"),
    
    # Data packages
    ("cent cinquante mega", "150Mo"),
    ("cinq giga par mois", "5Go/mois"),
    ("juróom go", "5Go"),
    
    # Currency amounts
    ("cinquante-quatre mille neuf cents francs cfa", "54 900 FCFA"),
    ("vingt mille francs", "20 000 F"),
    ("ñaar fukk junni francs", "20 000 F"),  # Wolof: 20 thousand francs
    
    # Phone numbers
    ("trente-trois huit cent trente-six trente-deux treize", "33 836 32 13"),
    ("sept huit sept sept huit trente-deux quarante", "78 778 32 40"),
    ("juróom ñaar fukk juróom ñett juróom ñaar fukk juróom ñett ñaar fukk", "77 77 20"),  # Wolof
    
    # Mixed Wolof numbers
    ("fukk ak juróom benn", "16"),  # 10 + 5 + 1
    ("ñaar fukk ak juróom ñaar", "27"),  # 20 + 5 + 2
    ("fanweer ak juróom", "35"),  # 30 + 5
    ("téeméer ak juróom ñaar fukk ak ñett", "173"),  # 100 + 70 + 3
    
    # Complex Wolof numbers
    ("junni ak juróom ñenti téeméer ak ñent fukk ak juróom", "1945"),  # 1000 + 900 + 40 + 5
    ("ñent junni ak juróom ñenti téeméer", "4900"),  # 4000 + 900
    
    # Currency in Wolof (dërëm = 5 FCFA)
    ("téeméeri dërëm", "500"),  # 100 × 5 FCFA
    ("ñaar fukk dërëm", "100"),  # 20 × 5 FCFA
]

# Run tests
print("Testing Senegal Voice Normalizer:\n")
for text, expected in test_cases:
    result = tokenizer.normalize(text)
    status = "✓" if result == expected else "✗"
    print(f"{status} Input: {text}")
    print(f"  Expected: {expected}")
    print(f"  Got: {result}")
    print()

# Test number conversion specifically
print("\nTesting Wolof number conversion:")
wolof_numbers = [
    ("benn", "1"),
    ("ñaar", "2"),
    ("ñett", "3"),
    ("ñent", "4"),
    ("juróom", "5"),
    ("juróom benn", "6"),
    ("juróom ñaar", "7"),
    ("juróom ñett", "8"),
    ("juróom ñent", "9"),
    ("fukk", "10"),
    ("fukk ak benn", "11"),
    ("ñaar fukk", "20"),
    ("fanweer", "30"),
    ("téeméer", "100"),
    ("junni", "1000"),
]

for wolof, expected in wolof_numbers:
    result = tokenizer.normalize(wolof)
    print(f"{wolof} -> {result} (expected: {expected})")