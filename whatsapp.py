import pywhatkit
import pyautogui
import time

def send_prescription(to_number, prescription_text):
    # Ensure +91 prefix
    to_number = str(to_number)
    if not to_number.startswith("+91"):
        to_number = "+91" + to_number.lstrip("0")

    phone_number = to_number
    message = prescription_text

    # Open WhatsApp chat with message
    pywhatkit.sendwhatmsg_instantly(phone_number, message, wait_time=10, tab_close=True)

    # Wait a few seconds for chat to load
    #
    # 
    time.sleep(5)

    # Press Enter to send
    pyautogui.press("enter")

    return(f"✅ Message sent instantly to {phone_number}")




#a=send_prescription(MOBILE_NUMBER, "helloooo")
#print(a)

