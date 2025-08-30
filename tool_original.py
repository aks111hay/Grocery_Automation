#!/usr/bin/env python3
import os
import json
import time
import sys
import re
from dotenv import load_dotenv
from langchain_core.tools import tool
from typing import List, Dict

from playwright.sync_api import sync_playwright
from browserbase import Browserbase
# Load environment variables
load_dotenv()

BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY") 
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")
bb = Browserbase(api_key=BROWSERBASE_API_KEY)
# Global holder for OTP input
# cart_json = None
zepto_otp = None

@tool
def set_zepto_otp(otp: str) -> None:
    """Set the OTP code for Zepto login."""
    global zepto_otp
    zepto_otp = otp

def manage_otp():
    otp = input("Enter OTP: ")
    return otp
# Default products if none provided
search_items = [
    "milk",
    "kurkure"
]

PHONE_NUMBER = "9334727093"
@tool
def run_zepto(PHONE_NUMBER : int, search_items : List[str], pincode: str = "560102") -> Dict:
    """
    Runs a Zepto search for the given phone number, list of search items,
    pincode for location selection and adds them to cart and Returns final pricing details.
    """

    print(f"Starting Zepto search for products: {search_items}")
    print(f"Using mobile number: {PHONE_NUMBER}")
    print(f"Using pincode: {pincode}")
    # Initialize BrowserBase variables   
    cart = {
        "merchant": "zepto",
        "total": 0,
        "cart_items": []
    }
    cart_json = {
        "merchant": "zepto",
        "total":0,
        "cart_items": []
    }
    # Initialize BrowserBase client
    with sync_playwright() as p:
        # ➜ Load or create context
        # context_id = load_context_id()
        # if context_id is None:
            # print("➡️ No saved context — creating new one...")



            # session = bb.sessions.create(
            #     project_id=BROWSERBASE_PROJECT_ID,
            #     proxies=True,
            #     browser_settings={
            #         "browser": "chromium",
            #         # "advanced_stealth": True,
            #     },
            # )
            # print(f"➡️ Session: https://browserbase.com/sessions/{session.id}")
            # chromium = p.chromium
            # browser = chromium.connect_over_cdp(session.connect_url)
            # context = browser.contexts[0]
            # page = context.pages[0]
            # Local Playwright session
            browser = p.chromium.launch(headless=False)  # set True for headless
            context = browser.new_context()
            page = context.new_page()
            print("➡️ Local Chromium browser launched")
            print("Opening Zepto...")
            try:
                print('Navigating to Zepto homepage for location selection...')
                page.goto('https://www.zepto.com/', timeout=20000)
                print('Successfully loaded Zepto homepage')
                
                # Wait for the page to stabilize
                page.wait_for_timeout(4000)
                
                # Location selection automation
                print('Starting location selection process...')
                
                # Step 1: Click on "Select Location" button
                print('Looking for Select Location button...')
                try:
                    location_button = page.wait_for_selector('button[aria-label="Select Location"]', timeout=10000)
                    location_button.click()
                    print('✅ Clicked Select Location button')
                    page.wait_for_timeout(2000)
                except Exception as e:
                    print(f'⚠️ Could not find Select Location button: {e}')
                    # Try alternative selector
                    try:
                        location_button = page.wait_for_selector('button[aria-haspopup="dialog"]', timeout=5000)
                        location_button.click()
                        print('✅ Clicked Select Location button (alternative selector)')
                        page.wait_for_timeout(2000)
                    except Exception as e2:
                        print(f'❌ Failed to click Select Location button: {e2}')
                
                # Step 2: Input pincode in search field
                print(f'Entering pincode: {pincode}')
                try:
                    search_input = page.wait_for_selector('input[placeholder="Search a new address"]', timeout=10000)
                    search_input.fill(pincode)
                    print('✅ Entered pincode in search field')
                    page.wait_for_timeout(3000)  # Wait for search results to load
                except Exception as e:
                    print(f'❌ Could not find or fill address search input: {e}')
                
                # Step 3: Select the first address from search results
                print('Selecting first address from search results...')
                try:
                    first_address = page.wait_for_selector('[data-testid="address-search-item"]', timeout=10000)
                    first_address.click()
                    print('✅ Selected first address from search results')
                    page.wait_for_timeout(2000)
                except Exception as e:
                    print(f'❌ Could not select first address: {e}')
                
                # Step 4: Click "Confirm & Continue" button
                print('Clicking Confirm & Continue button...')
                try:
                    confirm_button = page.wait_for_selector('button[data-testid="location-confirm-btn"]', timeout=10000)
                    confirm_button.click()
                    print('✅ Clicked Confirm & Continue button')
                    page.wait_for_timeout(3000)  # Wait for page to update
                except Exception as e:
                    print(f'❌ Could not click Confirm & Continue button: {e}')
                
                # # Step 5: Click on search bar before doing anything else
                # print('Clicking on search bar...')
                # try:
                #     search_bar = page.wait_for_selector('a[data-testid="search-bar-icon"]', timeout=10000)
                #     search_bar.click()
                #     print('✅ Clicked on search bar')
                #     page.wait_for_timeout(2000)
                    
                #     # Navigate to search page if not already there
                #     current_url = page.url
                #     if '/search' not in current_url:
                #         print('Navigating to search page...')
                #         page.goto('https://www.zepto.com/search', timeout=15000)
                #         page.wait_for_timeout(2000)
                #         print('✅ Navigated to search page')
                    
                # except Exception as e:
                #     print(f'⚠️ Could not click search bar, navigating directly to search: {e}')
                #     page.goto('https://www.zepto.com/search', timeout=15000)
                #     page.wait_for_timeout(2000)
                
                # print('✅ Location selection and search navigation completed')
                
            except Exception as e:
                print(f"⚠️ Error during location selection: {e}")
                print("Continuing with product search...")
            # Wait for the page to stabilize
            page.wait_for_timeout(4000)
            # Handle OTP input
            # try:
            #     # Wait for OTP input to appear with the exact selector from the HTML
            #     print('Waiting for OTP input field...')
            #     # Exact selector based on the provided HTML
            #     otp_selector = 'div.flex.w-full.justify-center.gap-x-2 input[type="text"][inputmode="numeric"]'
                
            #     print(f'Looking for OTP input with selector: {otp_selector}')
                
            #     # otp = manage_otp()
            #     while zepto_otp is None:
            #         print("Waiting for OTP...")
            #         time.sleep(1)
            #     otp = zepto_otp
            #     print(f'Received OTP: {zepto_otp.replace(zepto_otp, "*" * len(zepto_otp))}')
            #     # Try to enter OTP using Playwright's methods instead of JavaScript
            #     try:
            #         print('Entering OTP using Playwright methods...')
            #         # First try to find all OTP input fields
            #         otp_inputs = page.query_selector_all('div.flex.w-full.justify-center.gap-x-2 input[type="text"][inputmode="numeric"]')
                    
            #         if otp_inputs and len(otp_inputs) > 0:
            #             print(f'Found {len(otp_inputs)} OTP input fields')
                                
            #             # If we have multiple input fields (one for each digit)
            #             if len(otp_inputs) > 1:
            #                 for i, digit in enumerate(otp):
            #                     if i < len(otp_inputs):
            #                         otp_inputs[i].fill(digit)
            #                         print(f'Entered digit {i+1} of OTP')
            #             else:
            #                 # If there's just one field for the entire OTP
            #                 otp_inputs[0].fill(otp)
            #                 print('Entered full OTP in single field')
                        
            #             entered = True
            #         else:
            #             # Fallback to more generic selectors
            #             print('Using fallback selectors for OTP input...')
            #             fallback_selectors = [
            #                 'input[type="text"][inputmode="numeric"]',
            #                 'input[inputmode="numeric"]',
            #                 'input[type="tel"]',
            #                 'input[type="number"]'
            #             ]
                        
            #             for selector in fallback_selectors:
            #                 inputs = page.query_selector_all(selector)
            #                 if inputs and len(inputs) > 0:
            #                     print(f'Found {len(inputs)} inputs with selector {selector}')
                                
            #                     if len(inputs) == 1:
            #                         # Single input for all digits
            #                         inputs[0].fill(otp)
            #                         print('Entered full OTP in single field')
            #                     else:
            #                         # Multiple inputs for individual digits
            #                         for i, digit in enumerate(otp):
            #                             if i < len(inputs):
            #                                 inputs[i].fill(digit)
            #                                 print(f'Entered digit {i+1} of OTP')
                                        
            #                             entered = True
            #                             break
                                
            #                 if not entered:
            #                     print('Could not find any suitable OTP input fields')
            #                     entered = False
                            
            #                 if entered:
            #                     print('Successfully entered OTP using Playwright methods')
            #     except Exception as otp_error:
            #         print(f'Error entering OTP: {otp_error}')
                        
            #         # Wait for verification to complete
            #     try:
            #         print('OTP entered, waiting for verification to complete...')
            #         page.wait_for_timeout(2000)
            #         print('Continuing with product search...')
            #     except Exception as wait_error:
            #         print(f'Error waiting after OTP entry: {wait_error}')
            # except Exception as otp_error:
            #     print(f'Error handling OTP: {otp_error}')
                    
            # Search for each product and add to cart
            try:
                cart = {
                    "merchant": "zepto",
                    "total": 0,
                    "cart_items": []
                }
                        
                for i, product in enumerate(search_items):
                    print(f'\n=== Searching for product {i+1}: {product} ===')
                    
                    try:
                        # Navigate to search URL
                        search_url = f'https://www.zepto.com/search?query={product}'
                        print(f'Navigating to search URL: {search_url}')
                        page.goto(search_url, timeout=20000)
                        
                        # Wait for search results to load
                        page.wait_for_timeout(2000)
                        
                        # Look for add buttons
                        print('Looking for ADD buttons...')
                        
                        # Try to find and click the first ADD button
                        add_button_result = page.evaluate("""() => {
                            // Look for add buttons with various patterns
                            const addButtons = Array.from(document.querySelectorAll('button')).filter(btn => 
                                        btn.textContent.toLowerCase().includes('add') || 
                                        btn.innerText.toLowerCase().includes('add')
                                    );
                                    
                                    if (addButtons.length === 0) return { clicked: false, name: null, price: null };
                                    
                                    // Get the first product's name and price
                                    const productCard = addButtons[0].closest('div[class*="card"], div[class*="product"], div[class*="item"]');
                                    
                                    let name = null;
                                    let price = null;
                                    
                                    if (productCard) {
                                        // Try to find the product name
                                        const nameElements = Array.from(productCard.querySelectorAll('div, h3, h4, p')).filter(el => 
                                            !el.textContent.includes('₹') && 
                                            el.textContent.trim().length > 3 &&
                                            !el.textContent.toLowerCase().includes('add')
                                        );
                                        
                                        if (nameElements.length > 0) {
                                            name = nameElements[0].textContent.trim();
                                        }
                                        
                                        // Try to find the price
                                        const priceElements = Array.from(productCard.querySelectorAll('div, span, p')).filter(el => 
                                            el.textContent.includes('₹')
                                        );
                                        
                                        if (priceElements.length > 0) {
                                            const priceText = priceElements[0].textContent;
                                            const priceMatch = priceText.match(/₹\\s*([\\d,.]+)/);
                                            if (priceMatch) {
                                                price = parseFloat(priceMatch[1].replace(/,/g, ''));
                                            }
                                        }
                                    }
                                    
                                    // Click the add button
                                    addButtons[0].click();
                                    
                                    return { clicked: true, name, price };
                                }""")
                                
                        if add_button_result.get('clicked'):
                            print('Clicked ADD button for first product')
                                
                            # Add the product to our cart data
                            if add_button_result.get('name') and add_button_result.get('price'):
                                cart['cart_items'].append({
                                        'name': add_button_result['name'],
                                        'price': add_button_result['price']
                                    })
                                print(f'Added to cart: {add_button_result["name"]} - ₹{add_button_result["price"]}')
                            else:
                                print('Product added but could not extract name or price')
                        else:
                            print('No ADD buttons found for this product')
                                
                                # Wait a bit before searching for the next product
                        page.wait_for_timeout(1500)
                                
                    except Exception as search_error:
                        print(f'Error searching for product "{product}": {search_error}')
                        
                        # Navigate to cart to get the final total
                try:
                    print('\n=== Opening cart ===')
                        
                    try:
                        print("Waiting for Cart button...")
                        cart_button = page.wait_for_selector('a[aria-label="Cart"]', timeout=10000)
                        cart_button.click()
                        print("✅ Clicked Cart button successfully")
                        page.wait_for_timeout(2000)
                    except Exception as e:
                        print(f"❌ Failed to click cart button: {e}")

                                        # Check if login is required and click login button if present
                    try:
                        print("Checking if login is required...")
    
                        # Try to find the Login button
                        login_button = page.locator("button:has(h6:has-text('Login'))").first
                        
                        if login_button:
                            print("Login required, clicking Login button...")
                            login_button.click()
                            page.wait_for_timeout(2000)
                            print("✅ Clicked Login button")
                        
                            # Handle phone number input
                            print("Waiting for phone input field...")
                            page.wait_for_selector("input[type='tel']", timeout=30000)
                            print("📱 Phone input field found!")
                            # Enter phone number
                            print('Entering phone number...')
                            page.fill('input[type="tel"]', str(PHONE_NUMBER))
                            print(f'Entered phone number: {PHONE_NUMBER}')
                                    
                            # Click the continue button
                            print('Looking for continue button...')
                            try:
                                page.click('button:has-text("Continue")', timeout=3000)
                                print('Clicked continue button')
                            except Exception:
                                print('Could not find continue button, proceeding anyway')
                            
                            # Handle OTP input
                            try:
                                # Wait for OTP input to appear with the exact selector from the HTML
                                print('Waiting for OTP input field...')
                                # Exact selector based on the provided HTML
                                otp_selector = 'div.flex.w-full.justify-center.gap-x-2 input[type="text"][inputmode="numeric"]'
                                
                                print(f'Looking for OTP input with selector: {otp_selector}')
                                
                                # otp = manage_otp()
                                global zepto_otp
                                zepto_otp = None  # Reset OTP
                                
                                # Emit message to chat that OTP is needed (will be handled by the agent)
                                print("Waiting for Zepto OTP from chat interface...")
                                
                                # Wait for OTP to be set via set_zepto_otp function
                                max_wait_time = 300  # 5 minutes timeout
                                start_time = time.time()
                                
                                while zepto_otp is None:
                                    if time.time() - start_time > max_wait_time:
                                        raise Exception("OTP wait timeout exceeded (5 minutes)")
                                    print("Waiting for Zepto OTP input from chat...")
                                    time.sleep(2)  # Check every 2 seconds
                                
                                # Use the OTP received from chat
                                otp = zepto_otp
                                # Try to enter OTP using Playwright's methods instead of JavaScript
                                entered = False
                                try:
                                    print('Entering OTP using Playwright methods...')
                                    # First try to find all OTP input fields
                                    otp_inputs = page.query_selector_all('div.flex.w-full.justify-center.gap-x-2 input[type="text"][inputmode="numeric"]')
                                    
                                    if otp_inputs and len(otp_inputs) > 0:
                                        print(f'Found {len(otp_inputs)} OTP input fields')
                                                
                                        # If we have multiple input fields (one for each digit)
                                        if len(otp_inputs) > 1:
                                            for i, digit in enumerate(otp):
                                                if i < len(otp_inputs):
                                                    otp_inputs[i].fill(digit)
                                                    print(f'Entered digit {i+1} of OTP')
                                        else:
                                            # If there's just one field for the entire OTP
                                            otp_inputs[0].fill(otp)
                                            print('Entered full OTP in single field')
                                        
                                        entered = True
                                    else:
                                        # Fallback to more generic selectors
                                        print('Using fallback selectors for OTP input...')
                                        fallback_selectors = [
                                            'input[type="text"][inputmode="numeric"]',
                                            'input[inputmode="numeric"]',
                                            'input[type="tel"]',
                                            'input[type="number"]'
                                        ]
                                        
                                        for selector in fallback_selectors:
                                            inputs = page.query_selector_all(selector)
                                            if inputs and len(inputs) > 0:
                                                print(f'Found {len(inputs)} inputs with selector {selector}')
                                                
                                                if len(inputs) == 1:
                                                    # Single input for all digits
                                                    inputs[0].fill(otp)
                                                    print('Entered full OTP in single field')
                                                else:
                                                    # Multiple inputs for individual digits
                                                    for i, digit in enumerate(otp):
                                                        if i < len(inputs):
                                                            inputs[i].fill(digit)
                                                            print(f'Entered digit {i+1} of OTP')
                                                        
                                                entered = True
                                                break
                                                
                                        if not entered:
                                            print('Could not find any suitable OTP input fields')
                                            entered = False
                                        
                                        if entered:
                                            print('Successfully entered OTP using Playwright methods')
                                except Exception as otp_error:
                                    print(f'Error entering OTP: {otp_error}')
                                        
                                    # Wait for verification to complete
                                try:
                                    print('OTP entered, waiting for verification to complete...')
                                    page.wait_for_timeout(2000)
                                    print('Continuing with cart extraction...')
                                except Exception as wait_error:
                                    print(f'Error waiting after OTP entry: {wait_error}')
                            except Exception as otp_error:
                                print(f'Error handling OTP: {otp_error}')
                        else:
                            print("✅ Already logged in, no login required")
                    except Exception as login_check_error:
                        print(f"No login button found or already logged in: {login_check_error}")

                        
                    # Check for and handle Zepto Pass popup if it appears
                    try:
                        print('Checking for Zepto Pass popup...')

                        popup_visible = page.evaluate("""() => {
                            const popup = document.querySelector('div[class*="zepto-pass-cart"]');
                            return popup && popup.offsetParent !== null;
                        }""")

                        if popup_visible:
                            print('Zepto Pass popup detected, attempting to close it by clicking outside...')
                            
                            # Click top-left of the page (outside modal)
                            page.mouse.click(10, 10)

                            # Wait a moment for popup to disappear
                            page.wait_for_timeout(1000)

                            # Check if it's still visible
                            popup_still_there = page.evaluate("""() => {
                                const popup = document.querySelector('div[class*="zepto-pass-cart"]');
                                return popup && popup.offsetParent !== null;
                            }""")

                            if not popup_still_there:
                                print('✅ Popup closed successfully')
                            else:
                                print('⚠️ Popup still present — may need more specific logic')

                        else:
                            print('✅ No popup detected')

                    except Exception as popup_error:
                        print(f'❌ Error while handling popup: {popup_error}')

                            
                    # Additional wait to ensure cart is fully loaded
                    page.wait_for_load_state("domcontentloaded", timeout=1000)


                            
                    # Extract cart items using the exact DOM structure
                    try:
                        print('Extracting cart items...')

                        cart_items = page.evaluate("""() => {
                            const items = [];

                            // Each cart item is inside a flex div with padding
                            const itemContainers = document.querySelectorAll('div.flex.w-full.items-start.justify-between.py-2');

                            itemContainers.forEach(container => {
                                const nameEl = container.querySelector('p.text-skin-secondary-black');
                                const priceEl = container.querySelector('p.text-black');

                                if (nameEl && priceEl) {
                                    const name = nameEl.textContent.trim();

                                    // Filter out non-product items
                                    if (name.includes('To Pay') || name.includes('Tip') ||
                                        name.includes('Delivery') || name.includes('Add Custom')) {
                                        return;
                                    }

                                    const priceText = priceEl.textContent.trim();
                                    const match = priceText.match(/₹([\d,.]+)/);
                                    const price = match ? parseFloat(match[1].replace(/,/g, '')) : 0;

                                    if (price > 0) {
                                        items.push({
                                            name,
                                            price,
                                            quantity: 1  // default to 1; Zepto usually doesn't show exact quantity in DOM
                                        });
                                    }
                                }
                            });

                            return items;
                        }""")

                        if cart_items and len(cart_items) > 0:
                            print(f'Found {len(cart_items)} items in cart')
                            cart['cart_items'] = cart_items

                            for item in cart_items:
                                print(f"Added to cart: {item['name']} - ₹{item['price']} x {item['quantity']}")

                        else:
                            print('No items found in cart')

                    except Exception as items_extract_error:
                        print(f'Error extracting cart items: {items_extract_error}')
                        return cart

                    # ---------------------------
                    # Extract Total from "To Pay"
                    # ---------------------------
                    try:
                        print('Extracting cart total...')
                        
                        total_result = page.evaluate("""() => {
                            const totalEl = document.querySelector('span.text-cta1.truncate.text-left');
                            if (totalEl) {
                                const text = totalEl.textContent.trim();
                                const match = text.match(/₹([\d,.]+)/);
                                if (match) {
                                    const totalFloat = parseFloat(match[1].replace(/,/g, ''));
                                    return {
                                        total: Math.floor(totalFloat),
                                        found: true
                                    };
                                }
                            }
                            return { found: false };
                        }""")

                        if total_result.get('found'):
                            cart['total'] = total_result.get('total')
                            print(f'✅ Extracted cart total: ₹{cart["total"]}')
                            print(cart)
                            return cart
                        else:
                            print('⚠️ Could not extract total from DOM')
                            raise ValueError('Total not found in DOM')

                    except Exception as total_extract_error:
                        print(f'❌ Error extracting cart total: {total_extract_error}')
                        print('Calculating total manually from items...')
                    cart = json.dumps(cart)
                    return cart
                except Exception as cart_error:
                    print(f'Error navigating to cart or extracting total: {cart_error}')
                    # Calculate approximate total as fallback
                    cart['total'] = sum(item['price'] for item in cart['cart_items'])
                    # Round to 2 decimal places
                    cart['total'] = round(cart['total'], 2)
                    print(f'Using calculated total: ₹{cart["total"]}')
                    cart_json = json.dumps(cart)
                    return cart
                
            except Exception as navigation_error:
                print(f'Error navigating to Zepto: {navigation_error}')
                
            # Output the final cart data as JSON    
    return cart

    # For direct command-line usage
if __name__ == "__main__":
    result = run_zepto.invoke({"PHONE_NUMBER": PHONE_NUMBER, "search_items": search_items, "pincode": "560102"})
    print(result)