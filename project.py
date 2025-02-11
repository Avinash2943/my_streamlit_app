import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import os
import datetime

# Define file paths
stock_file_path = os.path.join(os.getcwd(), 'data', 'QUANTITY.ods')  # Stock file
threshold_file_path = os.path.join(os.getcwd(), 'data', 'ITEMS THRESHOLD.ods')  # Threshold file

# Function to load stock data from the .ods file
def load_stock_data():
    return pd.read_excel(stock_file_path, engine='odf')

# Function to load threshold data from the .ods file
def load_threshold_data():
    return pd.read_excel(threshold_file_path, engine='odf')

# Function to save updated stock data back to the .ods file
def save_stock_data(data):
    data.to_excel(stock_file_path, engine='odf', index=False)

# Function to save updated threshold data back to the .ods file
def save_threshold_data(data):
    data.to_excel(threshold_file_path, engine='odf', index=False)

# Load the data from both the stock and threshold files
stock_df = load_stock_data()
threshold_df = load_threshold_data()

# Set up the page configuration
st.set_page_config(page_title="Stock Count App", layout="wide")

# Display company logo and name on the homepage in side-by-side layout
col1, col2 = st.columns([1, 3])  # Define columns, adjust the ratio as needed

# Logo on the left
with col1:
    st.image(os.path.join(os.getcwd(), 'images', 'Logo.jpg'), use_container_width=True)  # Display the logo

# Company name on the right with large, attractive font
with col2:
    st.markdown(
        """
        <h1 style="color:#2e3d49; font-size: 88px; font-family: 'Arial', sans-serif; font-weight: bold;">
        West Cornwall Pasty
        </h1>
        """, 
        unsafe_allow_html=True
    )

# Sidebar for page navigation
page = st.sidebar.radio("Select Page", ["Current Stock", "Add New Stock", "Stock Movement"])

# Highlighting items in red if their stock is below the threshold
def highlight_below_threshold(row, threshold_data):
    item_name = row['ITEM']
    threshold_value = threshold_data.get(item_name)
    if threshold_value and row['QUANTITY'] < threshold_value:
        return ['background-color: red'] * len(row)
    return [''] * len(row)

# Create order list based on threshold comparison
def generate_order_list():
    order_list = []
    for _, row in stock_df.iterrows():
        item_name = row['ITEM']
        quantity = row['QUANTITY']
        
        # Get the threshold value for the current item
        threshold_value = threshold_df[threshold_df['ITEM'] == item_name]['THRESHOLD'].values
        
        # Check if the threshold value exists and if the quantity is below the threshold
        if threshold_value.size > 0 and quantity < threshold_value[0]:
            order_list.append({
                "Item": item_name,
                "Type": threshold_df[threshold_df['ITEM'] == item_name]['TYPE'].values[0],
                "Order Quantity": threshold_value[0] - quantity
            })
    return order_list

# Function to create a PDF from the order list
def generate_pdf(order_list):
    # Create a BytesIO buffer to save the PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica", 10)
    
    # Title of the PDF
    c.drawString(200, 750, "Order List (Items Below Threshold)")
    
    # Table headers
    c.drawString(30, 720, "Item")
    c.drawString(150, 720, "Type")
    c.drawString(250, 720, "Order Quantity")
    
    # Add the items to the table
    y_position = 700
    for item in order_list:
        c.drawString(30, y_position, item["Item"])
        c.drawString(150, y_position, item["Type"])
        c.drawString(250, y_position, str(item["Order Quantity"]))
        y_position -= 20
    
    # Save the PDF in the buffer
    c.showPage()
    c.save()
    
    # Get the PDF file content from the buffer
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data

# Function to handle the stock movement (recording items moved)
def record_stock_movement():
    # Display table with item names and input for stock moved
    movement_data = []

    # Use columns to display item name and stock moved input side by side
    for _, row in stock_df.iterrows():
        item_name = row['ITEM']
        opening_stock = row['QUANTITY']  # Opening stock is the current quantity in stock

        # Create two columns: one for the item name and one for the stock moved input field
        col1, col2 = st.columns([2, 1])  # Adjust column width ratio as needed

        with col1:
            st.text(item_name)  # Display the item name

        with col2:
            # Allow user to input stock moved
            stock_moved = st.number_input(f"Moved Quantity for {item_name}", min_value=0, step=1, key=item_name)
            movement_data.append({
                "ITEM": item_name,
                "OPENING_STOCK": opening_stock,
                "STOCK_MOVED": stock_moved,
                "CLOSING_STOCK": opening_stock - stock_moved
            })
    
    # After entering data, display the summary table for stock movement
    if st.button("Record Stock Movement"):
        # Create a DataFrame for the stock movement table
        movement_df = pd.DataFrame(movement_data)
        
        # Display the movement data (for review)
        st.subheader("Stock Movement Summary")
        st.dataframe(movement_df, use_container_width=True)

        # Update the stock quantity in the main stock file
        for index, row in movement_df.iterrows():
            item_name = row['ITEM']
            closing_stock = row['CLOSING_STOCK']
            
            # Update the stock quantity in the stock DataFrame
            stock_df.loc[stock_df["ITEM"] == item_name, "QUANTITY"] = closing_stock

        # Save the updated stock data back to the "QUANTITY.ods" file
        save_stock_data(stock_df)

        # Record the stock movement in a log or history file for future reference (optional)
        date_today = datetime.datetime.now().strftime("%Y-%m-%d")
        movement_df['DATE'] = date_today  # Add date to the movement table
        movement_df['ITEM'] = movement_df['ITEM'].astype(str)  # Ensure that the item column is in string format

        # Save stock movement to a history log file (optional)
        history_file_path = os.path.join(os.getcwd(), 'stock_movement_history.csv')
        if not os.path.exists(history_file_path):
            movement_df.to_csv(history_file_path, index=False)  # Create a new file if it doesn't exist
        else:
            movement_df.to_csv(history_file_path, mode='a', header=False, index=False)  # Append to the existing file

        st.success("Stock movement recorded and updated successfully!")

# Current Stock page
if page == "Current Stock":
    # Page for displaying the current stock count
    st.title("Current Stock Count")
    st.subheader("Here is the current stock inventory:")

    # Display stock table with highlighting of items below threshold
    styled_df = stock_df.style.apply(highlight_below_threshold, axis=1, threshold_data=threshold_df.set_index('ITEM')['THRESHOLD'].to_dict())
    st.dataframe(styled_df, use_container_width=True)

    # Option to add new items or delete items
    st.subheader("Add or Delete Stock Items")

    # Add new stock
    with st.expander("Add New Stock"):
        new_item = st.text_input("Enter New Item Name")  # Input field for new item
        new_type = st.selectbox("Select Item Type", ["box", "pack", "tub", "loaf", "individual", "roll"])  # Select item type
        new_quantity = st.number_input("Enter Quantity", min_value=0, step=1)  # Input for quantity
        new_threshold = st.number_input("Enter Threshold Value", min_value=0, step=1)  # Input for threshold

        if st.button("Add New Item"):
            if new_item and new_quantity > 0 and new_threshold > 0 and new_item not in stock_df["ITEM"].values:
                # If the item is not already in the stock, add it
                new_stock_data = pd.DataFrame({"ITEM": [new_item], "TYPE": [new_type], "QUANTITY": [new_quantity]})
                stock_df = pd.concat([stock_df, new_stock_data], ignore_index=True)
                
                # Also add the new item to the threshold data
                new_threshold_data = pd.DataFrame({"ITEM": [new_item], "TYPE": [new_type], "THRESHOLD": [new_threshold]})
                threshold_df = pd.concat([threshold_df, new_threshold_data], ignore_index=True)

                # Save both stock and threshold data
                save_stock_data(stock_df)
                save_threshold_data(threshold_df)

                st.success(f"Successfully added {new_item} to the stock and updated its threshold!")
            elif new_item in stock_df["ITEM"].values:
                st.error(f"{new_item} already exists in the stock!")
            else:
                st.error("Please enter a valid item name, quantity, and threshold.")

    # Delete stock item
    with st.expander("Delete Stock Item"):
        item_to_delete = st.selectbox("Select Item to Delete", stock_df["ITEM"])
        if st.button("Delete Item"):
            stock_df = stock_df[stock_df["ITEM"] != item_to_delete]
            threshold_df = threshold_df[threshold_df["ITEM"] != item_to_delete]  # Also remove from threshold table
            save_stock_data(stock_df)
            save_threshold_data(threshold_df)
            st.success(f"Successfully deleted {item_to_delete} from the stock.")

    # Generate the order list (items below threshold)
    order_list = generate_order_list()
    if order_list:
        st.subheader("Order List (Items Below Threshold)")
        order_df = pd.DataFrame(order_list)
        
        # Make the order list interactive using st.dataframe (built-in interactivity)
        st.dataframe(order_df, use_container_width=True)

        # Allow the order list to be downloaded as a PDF
        pdf_data = generate_pdf(order_list)
        st.download_button(
            label="Download Order List as PDF",
            data=pdf_data,
            file_name="order_list.pdf",
            mime="application/pdf"
        )

# Add New Stock page
elif page == "Add New Stock":
    # Page for adding new stock
    st.title("Add New Stock Item")
    st.subheader("Enter details of the new stock item below:")

    # Layout to display the input fields side by side using columns
    col1, col2 = st.columns(2)

    with col1:
        item = st.selectbox("Item Name", stock_df["ITEM"])
    with col2:
        quantity = st.number_input("New Quantity", min_value=0, step=1, format="%d")

    # Button to update the quantity in the stock table
    if st.button("Update Quantity"):
        # Check if quantity is provided
        if quantity > 0:
            # Find the row to update
            stock_df.loc[stock_df["ITEM"] == item, "QUANTITY"] = quantity
            save_stock_data(stock_df)  # Save updated data back to the file
            st.success(f"Successfully updated the quantity of {item} to {quantity}!")
        else:
            st.error("Please enter a valid quantity greater than zero.")

    # Display the updated stock table
    st.subheader("Updated Stock Table")
    st.dataframe(stock_df, use_container_width=True)

# Stock Movement page
elif page == "Stock Movement":
    st.title("Stock Movement")
    st.subheader("Enter the quantities of stock that have moved today:")
    
    # Record the stock movement data
    record_stock_movement()
