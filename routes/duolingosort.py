import json
import logging
from flask import request, jsonify
from routes import app
import re

# Setting up the logger
logger = logging.getLogger(__name__)

# Helper function to convert Roman numerals to integers
def roman_to_int(roman):
    roman_dict = {
        "I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000
    }
    total = 0
    prev_value = 0
    for char in reversed(roman):
        value = roman_dict[char]
        if value < prev_value:
            total -= value
        else:
            total += value
        prev_value = value
    return total

# Helper function to convert English words to integers
def english_to_int(english):
    english_dict = {
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
        "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
        "hundred": 100, "thousand": 1000
    }
    words = english.lower().split()
    result = 0
    temp = 0
    for word in words:
        if word in english_dict:
            value = english_dict[word]
            if value == 100 or value == 1000:
                temp *= value
            else:
                temp += value
    result += temp
    return result

# Helper function to convert Chinese numerals to integers (Simplified and Traditional)
def chinese_to_int(chinese):
    chinese_dict = {
        "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
        "十": 10, "百": 100, "千": 1000, "萬": 10000
    }
    
    chinese = chinese.replace("萬", "")  # For simplicity, we assume it's a smaller range.
    total = 0
    temp = 0
    for char in chinese:
        if char in chinese_dict:
            value = chinese_dict[char]
            if value == 10 or value == 100 or value == 1000:
                temp *= value
            else:
                temp += value
    total += temp
    return total

# Helper function to convert German words to integers
def german_to_int(german):
    german_dict = {
        "eins": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5,
        "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10,
        "zwanzig": 20, "dreißig": 30, "vierzig": 40, "fünfzig": 50,
        "hundert": 100, "tausend": 1000
    }
    words = german.lower().split()
    result = 0
    for word in words:
        if word in german_dict:
            result += german_dict[word]
    return result

# Helper function to get the numeric value of each representation
def get_numeric_value(value):
    if value.isdigit():  # Check if the value is an Arabic numeral
        return int(value)
    elif re.match(r"^[ivxlcdm]+$", value.lower()):  # Check if it's a Roman numeral
        return roman_to_int(value)
    elif "one" in value or "hundred" in value or "thousand" in value:  # Basic check for English numbers
        return english_to_int(value)
    elif re.match(r"[\u4e00-\u9fff]+", value):  # Check for Chinese characters
        return chinese_to_int(value)
    elif re.match(r"^[a-zA-Z]+$", value):  # Check if it's German (non-empty strings)
        return german_to_int(value)
    return 0  # Default for unsupported types

# Helper function to create a sorting key, considering language order
def sort_key(value):
    numeric_value = get_numeric_value(value)
    
    # Language ordering:
    # 0 -> Roman numerals
    # 1 -> English words
    # 2 -> Chinese (Simplified or Traditional) words
    # 3 -> German words
    # 4 -> Arabic numerals
    language_order = {
        'Roman': 0,
        'English': 1,
        'Chinese': 2,
        'German': 3,
        'Arabic': 4
    }

    # Determine the language type based on the value
    if re.match(r"^[ivxlcdm]+$", value.lower()):
        return (numeric_value, language_order['Roman'])
    elif "one" in value or "hundred" in value or "thousand" in value:
        return (numeric_value, language_order['English'])
    elif re.match(r"[\u4e00-\u9fff]+", value):
        return (numeric_value, language_order['Chinese'])
    elif re.match(r"^[a-zA-Z]+$", value):
        return (numeric_value, language_order['German'])
    else:
        return (numeric_value, language_order['Arabic'])

# Sorting logic for Part 1 (Roman and Arabic numerals only)
def sort_numbers_part_one(input_list):
    def sort_key(value):
        if value.isdigit():
            return int(value)
        else:
            return roman_to_int(value)
    
    sorted_numbers = sorted(input_list, key=sort_key)
    return [str(sort_key(value)) for value in sorted_numbers]

# Sorting logic for Part 2 (Multiple languages, including Roman numerals, English, Chinese, German, and Arabic)
def sort_numbers_part_two(input_list):
    # Sort the list using the key function that also respects language order
    return sorted(input_list, key=sort_key)

@app.route("/duolingo-sort", methods=["POST"])
def duolingo_sort():
    try:
        data = request.get_json(force=True)
        part = data.get("part")
        unsorted_list = data.get("challengeInput", {}).get("unsortedList", [])

        if not part or not unsorted_list:
            return jsonify({"error": "Missing required fields"}), 400
        
        if part == "ONE":
            sorted_list = sort_numbers_part_one(unsorted_list)
        elif part == "TWO":
            sorted_list = sort_numbers_part_two(unsorted_list)
        else:
            return jsonify({"error": "Invalid part value. Must be 'ONE' or 'TWO'"}), 400
        
        return jsonify({"sortedList": sorted_list})

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": "An error occurred while processing the request"}), 500
