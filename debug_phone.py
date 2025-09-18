#!/usr/bin/env python3
"""
Debug WhatsApp Phone Number Formatting
"""

def test_phone_formatting():
    """Test the phone number formatting logic."""
    
    test_numbers = [
        "2349022594853",  # Already formatted
        "09022594853",    # Nigerian format
        "9022594853",     # Without leading 0
        "+2349022594853", # With plus
        "2349022594853"   # Same as first
    ]
    
    for phone in test_numbers:
        print(f"\nTesting: {phone}")
        
        # Format phone number correctly for WhatsApp API
        # Remove any non-digit characters and ensure it starts with country code
        clean_number = ''.join(filter(str.isdigit, str(phone)))
        
        print(f"Cleaned: {clean_number}")
        
        if not clean_number.startswith('234') and len(clean_number) == 11:
            # Nigerian number without country code
            clean_number = '234' + clean_number[1:]
            print(f"Added country code (11 digits): {clean_number}")
        elif not clean_number.startswith('234') and len(clean_number) == 10:
            # Nigerian number without country code and leading 0
            clean_number = '234' + clean_number
            print(f"Added country code (10 digits): {clean_number}")
        elif len(clean_number) == 13 and clean_number.startswith('234'):
            # Already properly formatted
            print(f"Already properly formatted: {clean_number}")
        else:
            print(f"Unusual phone number format: {clean_number}")
        
        print(f"Final: {clean_number}")

if __name__ == "__main__":
    test_phone_formatting()
