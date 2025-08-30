#!/usr/bin/env python3
import os
import json
from pdb import run
import time
import re
import sys
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from browserbase import Browserbase
from langchain_core.tools import tool
from typing import List, Dict
load_dotenv()

BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")
bb = Browserbase(api_key=BROWSERBASE_API_KEY)
# Global holder for OTP input
# cart_json = None
blinkit_otp = None

@tool
def set_blinkit_otp(otp: str) -> None:
    """Set the OTP code for Blinkit login."""
    global blinkit_otp
    print(f"Setting Blinkit OTP: {otp}")
    blinkit_otp = otp
    return f"Blinkit OTP set: {otp}"

def manage_otp() -> str:
    otp = input("Enter OTP: ")
    return otp
# Default products if none provided
search_items = [
    "milk",
    "kurkure"
]

# Your address to search for
ADDRESS_TO_SEARCH = "560102"

# Default phone number for login
PHONE_NUMBER = "9334727093"
@tool
def run_blinkit(PHONE_NUMBER: int, search_items: List[str], ADDRESS_TO_SEARCH: str) -> Dict:
     
    """
    Runs a Blinkit search for the given phone number, list of search items,
    and address to search add all items to cart and  Returns final pricing details.
    """

    # Parse command line arguments
    if len(sys.argv) >= 2:
        try:
            # First argument is the products list as JSON
            search_items = json.loads(sys.argv[1])
            print(f"Using products from command line: {search_items}")
        except json.JSONDecodeError as e:
            print(f"Error parsing products from command line: {e}")
            print("Using default product list")
    
    # Second argument is the mobile number (if provided)
    if len(sys.argv) >= 3:
        PHONE_NUMBER = sys.argv[2]
        print(f"Using mobile number from command line: {PHONE_NUMBER}")
    
    with sync_playwright() as p:
        # Load or create context
        # context_id = load_context_id()
        # if context_id is None:
        
        
        # print(" No saved context — creating new one...")
        # session = bb.sessions.create(
        #     project_id=BROWSERBASE_PROJECT_ID,
        #     proxies=True,
        #     browser_settings={
        #         "browser": "chromium",
        #         # "advanced_stealth": True,
        #     },
        # )
        # print(f" Session: https://browserbase.com/sessions/{session.id}")
        # chromium = p.chromium
        # browser = chromium.connect_over_cdp(session.connect_url)
        # context = browser.contexts[0]
        # page = context.pages[0]


        # Local Playwright session
        browser = p.chromium.launch(headless=False)  # set True for headless
        context = browser.new_context()
        page = context.new_page()
        print(" Local Chromium browser launched")



        print("Opening Blinkit...")
        try:
            # Increase timeout to 30 seconds for initial page load
            print("Attempting to load Blinkit with 30 second timeout...")
            page.goto("https://blinkit.com/", wait_until="networkidle",timeout=5000)
            print(" Blinkit page loaded successfully")
        except Exception as e:
            print(f" Error loading Blinkit: {e}")
            print("Trying again with longer timeout and network idle strategy...")
            try:
                # Try again with an even longer timeout and different strategy
                page.goto("https://blinkit.com/", timeout=60000, wait_until="networkidle")
                print(" Blinkit page loaded on second attempt")
            except Exception as e:
                print(f" Failed to load Blinkit: {e}")
                print("Continuing anyway...")
                # Wait a bit to let any partial loading complete
                page.wait_for_timeout(5000)
        
        # Handle the location overlay that might be blocking interactions
        print("Checking for location overlay...")
        try:
            # Check if the location overlay is present
            location_overlay = page.locator('div.LocationDropDown__LocationOverlay-sc-bx29pc-1')
            try:
                location_overlay.wait_for(state='visible', timeout=5000)
                if location_overlay.is_visible():
                    print(" Found location overlay, handling it first")
                    
                    # Try to find the address input field
                    address_input = page.locator('input[name="select-locality"]')
                    try:
                        address_input.wait_for(state='visible', timeout=5000)
                        if address_input.is_visible():
                            print(f" Found address input field, entering address: {ADDRESS_TO_SEARCH}")
                            # Fill the address field
                            address_input.fill(ADDRESS_TO_SEARCH)
                            page.wait_for_timeout(2000)  # Wait for dropdown to appear
                            
                            # Try to find and click the first suggestion
                            try:
                                # Look for address suggestions
                                suggestions = page.locator('div.LocationSearchList__LocationListContainer-sc-93rfr7-0 div').all()
                                if len(suggestions) > 0:
                                    print(" Found address suggestions, clicking the first one")
                                    suggestions[0].click()
                                    page.wait_for_timeout(3000)  # Wait for selection to process
                                else:
                                    print(" No address suggestions found")
                                    
                                    # Try to find a confirm button if no suggestions appear
                                    confirm_button = page.locator('button:has-text("Confirm")')
                                    if confirm_button.is_visible():
                                        print(" Found confirm button, clicking it")
                                        confirm_button.click()
                                        page.wait_for_timeout(3000)
                            except Exception as e:
                                print(f" Error selecting address suggestion: {e}")
                                
                                # As a fallback, try to click outside the modal to dismiss it
                                try:
                                    print("Trying to click outside the modal to dismiss it...")
                                    page.mouse.click(10, 10)  # Click in the top-left corner
                                    page.wait_for_timeout(2000)
                                except Exception as e:
                                    print(f" Failed to dismiss modal: {e}")
                        else:
                            print(" Address input field not visible")
                    except Exception as e:
                        print(f" Error with address input field: {e}")
                else:
                    print("No location overlay found, continuing...")
            except Exception:
                print("No location overlay found, continuing...")
        except Exception as e:
            print(f" Error checking for location overlay: {e}")
            
        # Automated login process
        try:
            # Click on the login button
            print("Looking for login button...")
            page.wait_for_timeout(2000)  # Wait for page to stabilize
            
            # Try to find and click the login button
            login_button = page.locator('div.ProfileButton__Text-sc-975teb-2')
            try:
                login_button.wait_for(state='visible', timeout=5000)
                if login_button.is_visible():
                    print(" Found login button, clicking it")
                    login_button.click()
                    page.wait_for_timeout(2000)  # Wait for login modal to appear
                else:
                    print(" Login button not visible")
            except Exception as e:
                print(f" Error finding login button: {e}")
                
            # Enter phone number
            phone_input = page.locator('input[data-test-id="phone-no-text-box"]')
            try:
                phone_input.wait_for(state='visible', timeout=5000)
                if phone_input.is_visible():
                    print(f" Found phone input, entering number: {PHONE_NUMBER}")
                    phone_input.fill(str(PHONE_NUMBER))
                    page.wait_for_timeout(1000)  # Wait a bit after typing
                    
                    # Click the login/continue button
                    continue_button = page.locator('button.PhoneNumberLogin__LoginButton-sc-1j06udd-4')
                    if continue_button.is_visible():
                        print(" Clicking continue button to get OTP")
                        continue_button.click()
                        page.wait_for_timeout(2000)  # Wait for OTP screen
                        
                        # Wait for OTP to be received from chat interface
                        global blinkit_otp
                        blinkit_otp = None  # Reset OTP
                        
                        # Emit message to chat that OTP is needed (will be handled by the agent)
                        print("Waiting for Blinkit OTP from chat interface...")
                        
                        # Wait for OTP to be set via set_blinkit_otp function
                        max_wait_time = 300  # 5 minutes timeout
                        start_time = time.time()
                        
                        while blinkit_otp is None:
                            if time.time() - start_time > max_wait_time:
                                raise Exception("OTP wait timeout exceeded (5 minutes)")
                            print("Waiting for Blinkit OTP input from chat...")
                            time.sleep(2)  # Check every 2 seconds
                        
                        # Use the OTP received from chat
                        otp = blinkit_otp
                        
                        # Find OTP input fields and fill them
                        otp_inputs = page.locator('input[data-test-id="otp-text-box"]').all()
                        if len(otp_inputs) > 0:
                            print(" Found OTP input fields, filling OTP")
                            
                            # Fill each digit in the corresponding input field
                            for i, digit in enumerate(otp):
                                if i < len(otp_inputs):
                                    otp_inputs[i].fill(digit)
                                    page.wait_for_timeout(200)  # Small delay between digits
                            
                            print(" OTP entered successfully")
                            page.wait_for_timeout(3000)  # Wait for login to complete
                        else:
                            print(" OTP input fields not found")
                    else:
                        print(" Continue button not found")
                else:
                    print(" Phone input field not found")
            except Exception as e:
                print(f" Error during phone number entry: {e}")
                
        except Exception as e:
            print(f" Error during login process: {e}")
            print(" You may need to complete login manually.")
            input(" Press ENTER when you're ready to continue!")
        
        # Wait to ensure we're fully logged in and page is ready
        try:
            print("Waiting for page to be loaded after login...")
            # First wait for DOM content to be loaded (faster and more reliable)
            page.wait_for_load_state("domcontentloaded", timeout=5000)
            print(" DOM content loaded after login")
            
            # Try a brief network idle wait, but don't worry if it times out
            try:
                page.wait_for_load_state("networkidle", timeout=3000)
                print(" Network idle after login")
            except:
                print("Network still active after login, continuing anyway")
                
            # Short additional wait to ensure page is interactive
            page.wait_for_timeout(1000)
        except Exception as e:
            print(f" Error waiting for page to load after login: {e}")
            # Fallback wait
            page.wait_for_timeout(3000)
        

        # Search for each item using direct URL and add to cart
        for index, search_item in enumerate(search_items, start=1):
            print(f"\n=== Searching for product {index}: {search_item} ===")
            
            # Navigate directly to the search URL
            search_url = f"https://blinkit.com/s/?q={search_item}"
            print(f"Navigating to search URL: {search_url}")
            
            try:
                # Use a more robust loading strategy with increased timeout
                page.goto(search_url, wait_until="domcontentloaded", timeout=15000)
                print(" Search page loaded successfully")
                
                # Wait for the search results to load
                page.wait_for_timeout(3000)
                
                # Find all ADD buttons in the search results
                add_buttons = page.locator('div[role="button"] div:text-is("ADD")').all()
                
                if len(add_buttons) > 0:
                    print(f" Found {len(add_buttons)} products with ADD buttons")
                    
                    # Click on the first ADD button
                    print("Clicking on the first ADD button...")
                    add_buttons[0].click()
                    print(f" Added first {search_item} product to cart")
                    
                    # Wait for the add to cart animation
                    page.wait_for_timeout(2000)
                else:
                    print(f" No ADD buttons found for {search_item}")
                    
            except Exception as e:
                print(f" Error during search and add for {search_item}: {e}")
                continue
                
        # Function to extract cart details and return JSON output
        def extract_cart_details() -> Dict:
            try:
                print("\n=== Extracting cart details ===")
                
                # Extract cart items
                cart_items = []
                
                # Find all product cards in the cart
                product_cards = page.locator('div.DefaultProductCard__Container-sc-18qk0hu-3').all()
                print(f"Found {len(product_cards)} items in cart")
                
                total = 0
                
                for card in product_cards:
                    try:
                        # Extract product name
                        name_element = card.locator('div.DefaultProductCard__ProductTitle-sc-18qk0hu-6').first
                        name = name_element.text_content() if name_element.is_visible() else "Unknown Item"
                        
                        # Extract price
                        price_element = card.locator('div.DefaultProductCard__Price-sc-18qk0hu-15').first
                        price_text = price_element.text_content() if price_element.is_visible() else "₹0"
                        
                        # Extract numeric price value
                        price_match = re.search(r'₹(\d+)', price_text)
                        price = int(price_match.group(1)) if price_match else 0
                        
                        
                        # Add item to cart_items
                        cart_items.append({
                            "name": name,
                            "price": price
                        })
                        
                        print(f"Added item: {name} - ₹{price}")
                    except Exception as e:
                        print(f"Error extracting item details: {e}")
                total_element = page.locator('div.CheckoutStrip__TitleText-sc-1fzbdhy-9').first
                total = int(total_element.text_content().replace("₹", "").replace(",", ""))
                # Create the final JSON output
                cart_data = {
                    "merchant": "blinkit",
                    "total": total,
                    "cart_items": cart_items
                }
                
                return cart_data
            except Exception as e:
                print(f"Error extracting cart details: {e}")
                return {
                    "merchant": "blinkit",
                    "total": 0,
                    "cart_items": []
                }
                
        # After processing all products, open the cart
        print("\n=== Opening cart ===")
        cart_data = None
        try:
            # Try to find and click the cart button
            cart_button = page.locator('div.CartButton__Container-sc-1fuy2nj-3').first
            cart_button.click()
            print(" Clicked on cart button")
            page.wait_for_timeout(3000)  # Wait for cart to open
            
            # Extract cart details before checkout
            cart_data = extract_cart_details()
            
            # Return the cart data as JSON
            if cart_data:
                print("\n=== Cart Data JSON Output ===")
                cart_json = json.dumps(cart_data, indent=2)
                print(cart_json)
                return cart_data
        
                # Save cart data to file
                # with open("cart_data.json", "w") as f:
                #     f.write(cart_json)
                # print(" Cart data saved to cart_data.json")
                
            # Keep browser open for a while so user can see the results
            print("\n Browser will stay open for 60 seconds...")
            return cart_data
            
        except Exception as e:
            print(f" Failed to open cart: {e}")
            


        # if(input("should we proceed for checkout :--") == "y"):
        #     print("\n=== Proceeding to Checkout ===")
        #     print(" Clicked Proceed to Pay button")
        #     try:
        #         page.wait_for_load_state(wait_until="domcontentloaded", timeout=5000)
        #         print(" Checkout page loaded successfully")
        #     except:
        #         print("Network not fully idle for checkout, continuing anyway...")
        #     pay_button = page.locator('div[class*="Zpayments__PayNowButtonContainer-sc-127gezb-4 iCUOAj"]').first
        #     print(" Clicked Pay button1")
        #     pay_button.click()
        #     pay_button = page.locator('div[class*="Zpayments__Button-sc-127gezb-3 ejdFsx"]').first
        #     pay_button.click()
        #     print(" Clicked Pay button2")
        # else:
        #     print("\n=== Skipping Checkout ===")
            
        # print("\n Browser will stay open for 60 seconds...")
        browser.close()
        return cart_data

        
       

if __name__ == "__main__":
    result = run_blinkit.invoke({
    "PHONE_NUMBER": PHONE_NUMBER, 
    "search_items": search_items, 
    "ADDRESS_TO_SEARCH": ADDRESS_TO_SEARCH
    })
    print(result)
   