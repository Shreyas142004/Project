import re
import sys

# Dictionary for ISL Gloss to English natural sentence mapping
ISL_GRAMMAR_MAP = {
    "GOOD_MORNING": "Good morning.",
    "GOOD_AFTERNOON": "Good afternoon.",
    "GOOD_EVENING": "Good evening.",
    "GOOD_NIGHT": "Good night.",
    "GOOD_MORNING_GOOD_AFTERNOON_GOOD_EVENING_GOOD_NIGHT": "Good Morning. Good Afternoon. Good Evening. Good Night.",
    "HELLO": "Hello.",
    "THANK_YOU": "Thank you.",
    "PLEASE": "Please.",
    "HELP": "Help me.",
    "PLEASE_HELP": "Please help me.",
    "HOW_ARE_YOU": "How are you?",
    "WHAT_IS_YOUR_NAME": "What is your name?",
    "I_LOVE_YOU": "I love you.",
    "NICE_TO_MEET_YOU": "Nice to meet you.",
    "SEE_YOU_LATER": "See you later.",
    "TAKE_CARE": "Take care.",
    "SORRY": "I am sorry.",
    "WELCOME": "You are welcome.",
    "YES": "Yes.",
    "NO": "No.",
    "I": "I.",
    "YOU": "You.",
    "HE": "He.",
    "SHE": "She.",
    "WE": "We.",
    "THEY": "They.",
    "GROUND": "Ground.",
    "GREETINGS": "Greetings!"
}

def format_with_nlp(raw_input):
    """
    NLP Layer that converts raw sign language glosses/tokens into natural, 
    grammatically correct English sentences.
    """
    if not raw_input or not isinstance(raw_input, str):
        return "Sign language gesture recognized."

    cleaned = raw_input.strip()
    
    if cleaned in ["NO_HANDS_DETECTED", "NO_HANDS"]:
        return "No hands detected in the video."
        
    if cleaned in ["UNCERTAIN", "UNKNOWN"]:
        return "Sign language gesture recognized."

    # Check exact dictionary match
    upper_key = cleaned.upper().replace(' ', '_')
    if upper_key in ISL_GRAMMAR_MAP:
        return ISL_GRAMMAR_MAP[upper_key]

    # Handle numeric prefixes (e.g., "34. GROUND" -> "Ground.")
    cleaned = re.sub(r'^\d+\.\s*', '', cleaned)
    cleaned = cleaned.replace('_', ' ')

    # Convert ISL word sequences to natural sentence
    words = cleaned.split()
    if not words:
        return "Sign language gesture recognized."

    # Capitalize first letter and add period
    sentence = " ".join(words).lower()
    if len(sentence) > 0:
        sentence = sentence[0].upper() + sentence[1:]
    if not sentence.endswith(('.', '?', '!')):
        sentence += '.'

    return sentence

if __name__ == '__main__':
    test_str = sys.argv[1] if len(sys.argv) > 1 else "GOOD_MORNING"
    print(format_with_nlp(test_str))
