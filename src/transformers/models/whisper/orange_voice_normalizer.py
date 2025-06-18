# senegal_voice_normalizer.py
# Unified normalizer for Senegalese voice services
# Combines Wolof, French and Orange-specific normalization

import re
import unicodedata
from collections.abc import Iterator
from typing import List, Optional, Union

from .english_normalizer import remove_symbols_and_diacritics


class SenegalVoiceNormalizer:
    """
    Unified normalizer for Senegalese voice content that handles:
    - Wolof numbers (base-5 system)
    - French numbers
    - Mixed Wolof/French content
    - Orange telecom patterns (codes, data, phone numbers, prices)
    """
    
    def __init__(self):
        # Wolof number system (base-5)
        self.wolof_zeros = {"tus"}
        
        # Basic numbers 1-5
        self.wolof_basic = {
            "benn": 1, "ñaar": 2, "ñett": 3, "ñent": 4, "juróom": 5,
            # Alternative forms
            "ñaari": 2, "ñetti": 3, "ñenti": 4, "juróomi": 5,
            "benni": 1
        }
        
        # Ten
        self.wolof_ten = {"fukk": 10}
        
        # Hundreds
        self.wolof_hundred = {"téeméer": 100}
        
        # Thousands
        self.wolof_thousand = {"junni": 1000}
        
        # Special thirty
        self.wolof_special = {"fanweer": 30}
        
        # Large numbers
        self.wolof_large = {
            "fukki junni": 10000,
            "téeméeri junni": 100000,
            "tamndareet": 1000000,
            "million": 1000000,
            "tamñareet": 1000000000,
            "miliyard": 1000000000,
            "milliard": 1000000000
        }
        
        # French numbers
        self.french_ones = {
            "zéro": 0, "zero": 0, "un": 1, "une": 1, "deux": 2, "trois": 3,
            "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9,
            "dix": 10, "onze": 11, "douze": 12, "treize": 13, "quatorze": 14,
            "quinze": 15, "seize": 16, "dix-sept": 17, "dix-huit": 18, "dix-neuf": 19
        }
        
        self.french_tens = {
            "vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50,
            "soixante": 60, "soixante-dix": 70, "quatre-vingts": 80,
            "quatre-vingt": 80, "quatre-vingt-dix": 90
        }
        
        self.french_multipliers = {
            "cent": 100, "cents": 100, "mille": 1000,
            "million": 1000000, "millions": 1000000,
            "milliard": 1000000000, "milliards": 1000000000
        }
        
        # Special connectors
        self.connectors = {"ak", "et", "you", "manqué"}
        
        # Service words to remove in codes
        self.service_words = {"tapez", "composer", "appuyez", "sur"}
        
        # Orange patterns
        self.code_markers = ["dièse", "diese", "hash", "#", "étoile", "star", "*"]
        self.data_units = ["go", "mo", "giga", "mega", "gigaoctets", "megaoctets"]
        self.currency_markers = ["fcfa", "francs cfa", "francs", "f"]

    def normalize_codes(self, text: str) -> str:
        """Normalize service codes like 'tapez dièse 205 dièse' -> '#205#'"""
        # Remove service words before code patterns
        for word in self.service_words:
            text = re.sub(rf'\b{word}\s+(?=(dièse|diese|hash|étoile|star))', '', text, flags=re.IGNORECASE)
        
        # Pattern for codes with markers
        patterns = [
            (r'\b(dièse|diese|hash)\s+(.*?)\s+(dièse|diese|hash)\b', '#'),
            (r'\b(étoile|star)\s+(.*?)\s+(étoile|star)\b', '*'),
        ]
        
        for pattern, symbol in patterns:
            def replace_code(match):
                content = match.group(2)
                # Process the content to convert number words
                normalized = self.convert_to_number(content)
                return f"{symbol}{normalized}{symbol}"
            
            text = re.sub(pattern, replace_code, text, flags=re.IGNORECASE)
        
        return text

    def convert_to_number(self, text: str) -> str:
        """Convert number words to digits, handling both Wolof and French"""
        words = text.lower().split()
        result = []
        i = 0
        
        while i < len(words):
            # Handle hyphenated French numbers
            if '-' in words[i]:
                # Check if it's a compound French number
                if words[i] in self.french_tens:
                    result.append(str(self.french_tens[words[i]]))
                    i += 1
                    continue
                elif words[i] in self.french_ones:
                    result.append(str(self.french_ones[words[i]]))
                    i += 1
                    continue
                else:
                    # Try splitting hyphenated words
                    parts = words[i].split('-')
                    if len(parts) == 3 and parts[0] == "quatre" and parts[1] == "vingt":
                        # quatre-vingt-X
                        base = 80
                        if parts[2] in self.french_ones:
                            result.append(str(base + self.french_ones[parts[2]]))
                        else:
                            result.append(str(base))
                        i += 1
                        continue
                    elif len(parts) == 2:
                        # Regular hyphenated number
                        total = 0
                        for part in parts:
                            if part in self.french_ones:
                                total += self.french_ones[part]
                            elif part in self.french_tens:
                                total += self.french_tens[part]
                        if total > 0:
                            result.append(str(total))
                            i += 1
                            continue
            
            # Check if already a number
            if words[i].isdigit():
                result.append(words[i])
                i += 1
                continue
            
            # Try to match multi-word patterns (Wolof)
            matched = False
            
            # Check for "juróom X" patterns (5+X)
            if words[i] == "juróom" and i + 1 < len(words):
                if words[i+1] in self.wolof_basic:
                    value = 5 + self.wolof_basic[words[i+1]]
                    result.append(str(value))
                    i += 2
                    matched = True
                    continue
            
            # Check for "X fukk" patterns (X×10)
            if i + 1 < len(words) and words[i+1] == "fukk":
                if words[i] in self.wolof_basic:
                    value = self.wolof_basic[words[i]] * 10
                    result.append(str(value))
                    i += 2
                    matched = True
                    continue
                elif words[i] == "juróom":
                    # Check for "juróom X fukk" (5+X)×10
                    if i + 2 < len(words) and words[i+2] == "fukk":
                        i += 1  # Skip juróom
                        if words[i] in self.wolof_basic:
                            value = (5 + self.wolof_basic[words[i]]) * 10
                            result.append(str(value))
                            i += 2
                            matched = True
                            continue
            
            # Check for "X téeméer" patterns (X×100)
            if i + 1 < len(words) and words[i+1] == "téeméer":
                if words[i] in self.wolof_basic:
                    value = self.wolof_basic[words[i]] * 100
                    result.append(str(value))
                    i += 2
                    matched = True
                    continue
                elif words[i] == "juróom":
                    # Check for "juróom X téeméer" (5+X)×100
                    if i + 2 < len(words) and words[i+2] == "téeméer":
                        i += 1  # Skip juróom
                        if words[i] in self.wolof_basic:
                            value = (5 + self.wolof_basic[words[i]]) * 100
                            result.append(str(value))
                            i += 2
                            matched = True
                            continue
            
            # Check for "X junni" patterns - BUT NOT for standalone "fukk junni" or "ñaar fukk junni"
            if i + 1 < len(words) and words[i+1] == "junni":
                # For "ñaar fukk junni", we should have already processed "ñaar fukk" as 20
                # So don't process "fukk junni" separately
                if words[i] in self.wolof_basic and not (i > 0 and result and result[-1] == "20"):
                    value = self.wolof_basic[words[i]] * 1000
                    result.append(str(value))
                    i += 2
                    matched = True
                    continue
            
            if matched:
                continue
            
            # Check single word conversions
            if words[i] in self.wolof_basic:
                result.append(str(self.wolof_basic[words[i]]))
            elif words[i] in self.wolof_ten:
                result.append(str(self.wolof_ten[words[i]]))
            elif words[i] in self.wolof_hundred:
                result.append(str(self.wolof_hundred[words[i]]))
            elif words[i] in self.wolof_thousand:
                result.append(str(self.wolof_thousand[words[i]]))
            elif words[i] in self.wolof_special:
                result.append(str(self.wolof_special[words[i]]))
            elif words[i] in self.french_ones:
                result.append(str(self.french_ones[words[i]]))
            elif words[i] in self.french_tens:
                result.append(str(self.french_tens[words[i]]))
            elif words[i] in self.french_multipliers:
                result.append(str(self.french_multipliers[words[i]]))
            elif words[i] == "dërëm":
                result.append("dërëm")
            elif words[i] in self.connectors:
                result.append(words[i])
            else:
                result.append(words[i])
            
            i += 1
        
        # Now calculate the final number
        return self.calculate_from_parts(result)

    def calculate_from_parts(self, parts: List[str]) -> str:
        """Calculate the final number from parts, handling 'ak' and multiplication"""
        # First handle 'ak' (addition)
        while "ak" in parts:
            idx = parts.index("ak")
            if idx > 0 and idx < len(parts) - 1:
                left = parts[idx-1]
                right = parts[idx+1]
                if left.isdigit() and right.isdigit():
                    sum_val = int(left) + int(right)
                    parts = parts[:idx-1] + [str(sum_val)] + parts[idx+2:]
                else:
                    parts.remove("ak")
            else:
                parts.remove("ak")
        
        # Now handle multiplication and combination
        numbers = []
        other_words = []
        
        for part in parts:
            if part.isdigit():
                numbers.append(int(part))
            elif part == "dërëm" and numbers:
                # Multiply last number by 5
                numbers[-1] = numbers[-1] * 5
            else:
                other_words.append(part)
        
        if not numbers:
            return ' '.join(parts)
        
        # Combine numbers based on French/Wolof rules
        result_numbers = []
        i = 0
        
        while i < len(numbers):
            current = numbers[i]
            
            # Look ahead for multipliers
            if i + 1 < len(numbers):
                next_num = numbers[i + 1]
                # Check if next number is a multiplier (100, 1000, etc.)
                if next_num >= 100 and current < next_num:
                    # Multiply current by next
                    result_numbers.append(current * next_num)
                    i += 2
                    continue
            
            # No multiplication, just add the number
            result_numbers.append(current)
            i += 1
        
        # Sum all the result numbers
        total = sum(result_numbers)
        
        # If we have other words, return them with the number
        if other_words:
            return str(total) + ' ' + ' '.join(other_words)
        
        return str(total)

    def normalize_phone_numbers(self, text: str) -> str:
        """Detect and format phone numbers (only French spoken)"""
        words = text.split()
        result = []
        i = 0
        
        while i < len(words):
            # Look for sequences that could be phone numbers
            phone_parts = []
            j = i
            
            # Collect potential phone number parts (only French numbers)
            while j < len(words) and len(phone_parts) < 12:
                word = words[j]
                # Convert word to number if possible
                if word.isdigit():
                    phone_parts.append(word)
                elif word in self.french_ones:
                    phone_parts.append(str(self.french_ones[word]))
                elif word in self.french_tens:
                    phone_parts.append(str(self.french_tens[word]))
                elif word == "cent":
                    # Skip "cent" in phone number context
                    j += 1
                    continue
                elif word in ["et", "-"]:
                    # Skip connectors in phone context
                    j += 1
                    continue
                else:
                    # Not a phone number part
                    break
                j += 1
            
            # Check if we have a potential phone number (6-10 parts)
            if len(phone_parts) >= 6:
                # Convert to single digits where needed
                digits = []
                for part in phone_parts:
                    if len(part) == 1 or (len(part) == 2 and part[0] in "789"):
                        digits.append(part)
                    else:
                        # Not a phone digit pattern
                        break
                
                # Check if we have 8 or 9 digits
                digit_str = ''.join(digits)
                if len(digit_str) in [8, 9]:
                    # Format as phone number
                    if len(digit_str) == 9:
                        formatted = f"{digit_str[0:2]} {digit_str[2:5]} {digit_str[5:7]} {digit_str[7:9]}"
                    else:
                        formatted = f"{digit_str[0:2]} {digit_str[2:5]} {digit_str[5:8]}"
                    result.append(formatted)
                    i = j
                    continue
            
            # Not a phone number, process normally
            result.append(words[i])
            i += 1
        
        return ' '.join(result)

    def normalize_data(self, text: str) -> str:
        """Normalize data quantities like 'cinq giga' -> '5Go'"""
        pattern = r'\b(.*?)\s+(go|mo|giga|mega|gigaoctets?|megaoctets?)\b'
        
        def replace_data(match):
            quantity = match.group(1).strip()
            unit = match.group(2).lower()
            
            # Convert quantity to number
            normalized_qty = self.convert_to_number(quantity)
            
            # Standardize unit
            if unit in ['go', 'giga', 'gigaoctets', 'gigaoctet']:
                unit = 'Go'
            elif unit in ['mo', 'mega', 'megaoctets', 'megaoctet']:
                unit = 'Mo'
            
            return f"{normalized_qty}{unit}"
        
        text = re.sub(pattern, replace_data, text, flags=re.IGNORECASE)
        
        # Handle per month patterns
        text = re.sub(r'(\d+)(Go|Mo)\s*/\s*mois', r'\1\2/mois', text)
        text = re.sub(r'(\d+)(Go|Mo)\s+par\s+mois', r'\1\2/mois', text)
        
        return text

    def normalize_currency(self, text: str) -> str:
        """Normalize currency amounts with proper formatting"""
        patterns = [
            (r'\b(.*?)\s+(francs?\s+cfa|fcfa)\b', 'FCFA'),
            (r'\b(.*?)\s+francs?\b', 'F'),
            (r'\b(.*?)\s+f\b', 'F'),
        ]
        
        for pattern, currency in patterns:
            def replace_currency(match):
                amount = match.group(1).strip()
                
                # Convert amount to number
                if "dërëm" in amount:
                    # Special handling for dërëm
                    words = amount.split()
                    if words[-1] == "dërëm" and len(words) > 1:
                        # Get the number before dërëm
                        num_part = ' '.join(words[:-1])
                        base_num = self.convert_to_number(num_part)
                        if base_num.isdigit():
                            normalized = str(int(base_num) * 5)
                        else:
                            normalized = amount
                    else:
                        normalized = self.convert_to_number(amount)
                else:
                    # Process the amount text as a whole
                    normalized = self.convert_to_number(amount)
                
                # Format large numbers with spaces
                if normalized.isdigit() and len(normalized) >= 4:
                    formatted = self._format_with_spaces(normalized)
                    return f"{formatted} {currency}"
                return f"{normalized} {currency}"
            
            text = re.sub(pattern, replace_currency, text, flags=re.IGNORECASE)
        
        return text

    def _format_with_spaces(self, number_str: str) -> str:
        """Add spaces every 3 digits from right"""
        if len(number_str) <= 3:
            return number_str
        
        # Reverse, add spaces, reverse again
        reversed_str = number_str[::-1]
        spaced = ' '.join([reversed_str[i:i+3] for i in range(0, len(reversed_str), 3)])
        return spaced[::-1]

    def __call__(self, text: str) -> str:
        """Main normalization pipeline"""
        # Step 1: Normalize service codes first
        text = self.normalize_codes(text)
        
        # Step 2: Normalize phone numbers
        text = self.normalize_phone_numbers(text)
        
        # Step 3: Apply other normalizations
        text = self.normalize_data(text)
        
        # Step 4: Special handling for currency to ensure multiplication works
        # Process the text word by word, looking for patterns like "number word(s) currency"
        words = text.split()
        result = []
        i = 0
        
        while i < len(words):
            # Check if this could be start of a currency amount
            if i < len(words) - 1:
                # Look ahead for currency markers
                currency_found = False
                currency_idx = -1
                currency_type = ""
                
                # Check next few words for currency markers
                for j in range(i + 1, min(i + 6, len(words))):
                    if words[j].lower() in ["francs", "franc", "f"]:
                        currency_found = True
                        currency_idx = j
                        currency_type = "F"
                        break
                    elif words[j].lower() in ["fcfa"] or (j < len(words) - 1 and words[j].lower() == "francs" and words[j+1].lower() == "cfa"):
                        currency_found = True
                        currency_idx = j
                        currency_type = "FCFA"
                        if words[j].lower() == "francs":
                            currency_idx = j + 1  # Skip "cfa" too
                        break
                
                if currency_found:
                    # Extract the amount part
                    amount_text = " ".join(words[i:currency_idx])
                    
                    # Convert to number
                    if "dërëm" in amount_text:
                        # Special handling for dërëm
                        parts = amount_text.split()
                        if parts[-1] == "dërëm" and len(parts) > 1:
                            num_part = ' '.join(parts[:-1])
                            base_num = self.convert_to_number(num_part)
                            if base_num.isdigit():
                                normalized = str(int(base_num) * 5)
                            else:
                                normalized = amount_text
                        else:
                            normalized = self.convert_to_number(amount_text)
                    else:
                        normalized = self.convert_to_number(amount_text)
                    
                    # Format large numbers
                    if normalized.isdigit() and len(normalized) >= 4:
                        formatted = self._format_with_spaces(normalized)
                        result.append(f"{formatted} {currency_type}")
                    else:
                        result.append(f"{normalized} {currency_type}")
                    
                    # Skip to after currency marker
                    i = currency_idx + 1
                    if currency_type == "FCFA" and currency_idx < len(words) and words[currency_idx-1].lower() == "francs":
                        i = currency_idx + 1  # Skip "cfa"
                    continue
            
            # Not currency, just add the word
            result.append(words[i])
            i += 1
        
        text = ' '.join(result)
        
        # Step 5: Clean up
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text