import json
import logging
from routes import app
import re
from functools import cmp_to_key
from flask import Flask, request, jsonify
import re

# Setting up the logger
logger = logging.getLogger(__name__)


# --- Part 1: Roman and Arabic Numeral Sorting ---

def roman_to_int(s: str) -> int:
    """Converts a Roman numeral string to an integer."""
    roman_map = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    result = 0
    for i in range(len(s)):
        # Handle subtractive cases like IV, IX, XL, etc.
        if i > 0 and roman_map[s[i]] > roman_map[s[i-1]]:
            result += roman_map[s[i]] - 2 * roman_map[s[i-1]]
        else:
            result += roman_map[s[i]]
    return result

def solve_part_one(str_list: list[str]) -> list[str]:
    """Solves Part 1 of the challenge."""
    numeric_values = []
    for s in str_list:
        if s.isdigit():
            numeric_values.append(int(s))
        else:
            numeric_values.append(roman_to_int(s))
            
    numeric_values.sort()
    
    return [str(val) for val in numeric_values]

# --- Part 2: Multi-language Sorting ---

class NumberParser:
    """
    A comprehensive parser to identify the language of a number string,
    convert it to its integer value, and assign a sort order for tie-breaking.
    """
    # Predefined order for tie-breaking
    LANG_ORDER = {
        'roman': 0, 'english': 1, 'traditional_chinese': 2,
        'simplified_chinese': 3, 'german': 4, 'arabic': 5
    }

    # Dictionaries for parsing different languages
    ROMAN_CHARS = set('IVXLCDM')
    
    # Chinese number maps
    CH_NUM = {'零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
              '两': 2, '壹': 1, '貳': 2, '叁': 3, '肆': 4, '伍': 5, '陸': 6, '柒': 7, '捌': 8, '玖': 9}
    CH_MULT_SIMP = {'十': 10, '百': 100, '千': 1000, '万': 10000, '亿': 100000000}
    CH_MULT_TRAD = {'拾': 10, '佰': 100, '仟': 1000, '萬': 10000, '億': 100000000}
    
    # English and German number maps
    EN_WORDS = {'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70, 'eighty': 80, 'ninety': 90}
    EN_MULTS = {'hundred': 100, 'thousand': 1000, 'million': 1000000}
    
    DE_WORDS = {'null': 0, 'eins': 1, 'zwei': 2, 'drei': 3, 'vier': 4, 'fünf': 5, 'sechs': 6, 'sieben': 7, 'acht': 8, 'neun': 9, 'zehn': 10, 'elf': 11, 'zwölf': 12, 'dreizehn': 13, 'vierzehn': 14, 'fünfzehn': 15, 'sechzehn': 16, 'siebzehn': 17, 'achtzehn': 18, 'neunzehn': 19, 'zwanzig': 20, 'dreißig': 30, 'vierzig': 40, 'fünfzig': 50, 'sechzig': 60, 'siebzig': 70, 'achtzig': 80, 'neunzig': 90}
    DE_MULTS = {'hundert': 100, 'tausend': 1000, 'million': 1000000}


    def __init__(self, original_string: str):
        self.original = original_string
        self.value, self.lang_order = self._parse(original_string)

    def _parse(self, s: str):
        """Master parse method to detect language and convert to integer."""
        # Arabic
        if s.isdigit():
            return int(s), self.LANG_ORDER['arabic']
        # Roman
        if all(c in self.ROMAN_CHARS for c in s):
            return roman_to_int(s), self.LANG_ORDER['roman']
        # Chinese
        if any(c in self.CH_NUM or c in self.CH_MULT_SIMP or c in self.CH_MULT_TRAD for c in s):
            is_trad = any(c in self.CH_MULT_TRAD or c in '壹貳叁肆伍陸柒捌玖' for c in s)
            lang = 'traditional_chinese' if is_trad else 'simplified_chinese'
            return self._chinese_to_int(s), self.LANG_ORDER[lang]
        # German vs English
        words = re.split(r'[\s-]+', s.lower())
        if any(w in self.DE_WORDS or w in self.DE_MULTS for w in words):
            return self._german_to_int(s), self.LANG_ORDER['german']
        if any(w in self.EN_WORDS or w in self.EN_MULTS for w in words):
            return self._english_to_int(s), self.LANG_ORDER['english']
        
        # Fallback
        return 0, 99

    def _english_to_int(self, s: str) -> int:
        words = re.split(r'[\s-]+', s.lower())
        total = 0
        current_val = 0
        for word in words:
            if word in self.EN_WORDS:
                current_val += self.EN_WORDS[word]
            elif word in self.EN_MULTS:
                current_val *= self.EN_MULTS[word]
                if self.EN_MULTS[word] >= 1000: # thousand, million
                    total += current_val
                    current_val = 0
        total += current_val
        return total
    
    def _german_to_int(self, s: str) -> int:
        s = s.lower()
        # Handle cases like "siebenundachtzig" (seven and eighty)
        if 'und' in s:
            parts = s.split('und')
            return self.DE_WORDS[parts[0]] + self._german_to_int(parts[1])
        
        words = re.split(r'[\s-]+', s)
        total = 0
        current_val = 0
        for word in words:
            if word in self.DE_WORDS:
                current_val += self.DE_WORDS[word]
            elif word in self.DE_MULTS:
                # Handle cases like 'einhundert' -> 100 not 1*100
                if current_val == 0:
                    current_val = 1
                current_val *= self.DE_MULTS[word]
                if self.DE_MULTS[word] >= 1000:
                    total += current_val
                    current_val = 0
        total += current_val
        return total

    def _chinese_to_int(self, s: str) -> int:
        all_mults = {**self.CH_MULT_SIMP, **self.CH_MULT_TRAD}
        # Normalize to use a single character set for logic
        s = s.replace('兩', '二').replace('万', '萬').replace('亿', '億')
        
        def parse_chunk(chunk):
            if not chunk: return 0
            
            # Handle initial 十 e.g., 十五 -> 15
            if chunk.startswith(('十', '拾')):
                chunk = '一' + chunk

            val = 0
            temp_num = 0
            for char in chunk:
                if char in self.CH_NUM:
                    temp_num = self.CH_NUM[char]
                elif char in all_mults:
                    val += temp_num * all_mults[char]
                    temp_num = 0
            val += temp_num
            return val

        total = 0
        if '億' in s:
            parts = s.split('億', 1)
            total += parse_chunk(parts[0]) * 100000000
            s = parts[1]
        if '萬' in s:
            parts = s.split('萬', 1)
            total += parse_chunk(parts[0]) * 10000
            s = parts[1]
        
        total += parse_chunk(s)
        return total

def solve_part_two(str_list: list[str]) -> list[str]:
    """Solves Part 2 of the challenge using a custom sort key."""
    parsed_numbers = [NumberParser(s) for s in str_list]
    
    # Sort first by numeric value, then by the predefined language order
    sorted_numbers = sorted(parsed_numbers, key=lambda x: (x.value, x.lang_order))
    
    return [item.original for item in sorted_numbers]


# --- Flask Endpoint ---

@app.route("/duolingo-sort", methods=["POST"])
def duolingo_sort_handler():
    """Main endpoint to handle sorting requests."""
    try:
        data = request.get_json()
        part = data.get("part")
        challenge_input = data.get("challengeInput", {})
        unsorted_list = challenge_input.get("unsortedList", [])

        if not part or not isinstance(unsorted_list, list):
            return jsonify({"error": "Invalid input format"}), 400

        if part == "ONE":
            sorted_list = solve_part_one(unsorted_list)
        elif part == "TWO":
            sorted_list = solve_part_two(unsorted_list)
        else:
            return jsonify({"error": f"Part '{part}' is not supported"}), 400

        return jsonify({"sortedList": sorted_list})

    except Exception as e:
        # Log the exception in a real application
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal server error occurred"}), 500

