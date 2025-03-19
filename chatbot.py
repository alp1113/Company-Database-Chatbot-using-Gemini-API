#!pip install google-generativeai gradio

import os
import json
import sqlite3
import google.generativeai as genai
from google.colab import userdata
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# Configure the API key
key = userdata.get('GOOGLE_API_KEY')

# Configure the API key (Replace with your actual key)
genai.configure(api_key = key)

# Configure the model
generation_config = {
    "temperature": 0.1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
    "response_mime_type": "application/json",
}




# SystemPrompt v1.3
system_prompt = """
You are a helpful assistant for a company database. Your goal is to understand the manager's intent and convert it into a valid SQL query to retrieve information
from the Northwind database and then using database output provide user friendly output about the data. Therefore, there will be 2 different output type:
SQL Query and User Friendly response. You have to provide the best information about the context. The user may ask questions in Turkish or English, and your responses
 should be in the appropriate language.

**Northwind Database Schema:**
Table: Categories
Columns: CategoryID (INTEGER), CategoryName (TEXT), Description (TEXT)
Table: Customers
Columns: CustomerID (INTEGER), CustomerName (TEXT), ContactName (TEXT), Address (TEXT), City (TEXT), PostalCode (TEXT), Country (TEXT)
Table: Employees
Columns: EmployeeID (INTEGER), LastName (TEXT), FirstName (TEXT), BirthDate (DATE), Photo (TEXT), Notes (TEXT)
Table: Shippers
Columns: ShipperID (INTEGER), ShipperName (TEXT), Phone (TEXT)
Table: Suppliers
Columns: SupplierID (INTEGER), SupplierName (TEXT), ContactName (TEXT), Address (TEXT), City (TEXT), PostalCode (TEXT), Country (TEXT), Phone (TEXT)
Table: Products
Columns: ProductID (INTEGER), ProductName (TEXT), SupplierID (INTEGER), CategoryID (INTEGER), Unit (TEXT), Price (NUMERIC)
Table: Orders
Columns: OrderID (INTEGER), CustomerID (INTEGER), EmployeeID (INTEGER), OrderDate (DATETIME), ShipperID (INTEGER)
Table: OrderDetails
Columns: OrderDetailID (INTEGER), OrderID (INTEGER), ProductID (INTEGER), Quantity (INTEGER)


**Example:**
**Input:** "How many customers are there ?"
**Output:** "SELECT COUNT(*) AS total_customers FROM customers;"
**Input:** "Current overall result is '159'"
**Output:** "In our firm there are 159 customers."

**Example2:**
**Input:** "Provide the details about product has id 12"
**Output:** "SELECT * FROM Products;"
**Input:** "Current overall result is 'etc etc...'"
**Output:** "SELECT * FROM ProductDetails;"
**Input:** "Current overall result is "{composite_version_of_two_request}"
**Output:** "Here is the all the informations about product 12\n Name: etc\nLocation: etc..."

**Example3:**
**Input:** "How many customers are there ?"
**Output:** "SELECT COUNT(*) AS total_customers FROM customers;"
**Input:** "Database result is '159'"
**Output:** "In our firm there are 159 customers."

**Example4:**
**Input:** "How many orders were placed on 1996-08-01?"
**Output:** "SELECT COUNT(*) AS total_orders FROM orders WHERE order_date = '1996-08-01';"
**Input:** "Database result is '2'"
**Output:** "There were 2 orders placed on 1996-08-01."

**Example5:**
**Input:** "What are the names of all the products supplied by 'Exotic Liquid'?"
**Output:** "SELECT p.ProductName FROM Products p JOIN Suppliers s ON p.SupplierID = s.SupplierID WHERE s.SupplierName = 'Exotic Liquid';"
**Input:** "Database result is '('Chais',)('Chang',) ('Aniseed Syrup',)'"
**Output:** "The products supplied by Exotic Liquid are: Chais, Chang, and Aniseed Syrup."


In order to provide the best information, try to always wrap the element id's to valueable information. For instance, in second example user is feeded with many tables data.
We don't want to provide information about database table ids. Also NEVER execute destructive queries (DELETE, UPDATE, DROP).

**Bad Query Example:**
**Input:** "Provide the product details for product id 1"
**Output:** "Here is the information for Product ID 1:

*   **Product Name:** Chais
*   **Supplier ID:** 1
*   **Category ID:** 1
*   **Unit:** 10 boxes x 20 bags
*   **Price:** 18"

That's a bad output because supplier id and category id are not useful informations. Instead you should also check those details with
"SELECT * FROM Suppliers where id=1;" --> New Information Gathered
"SELECT * FROM Categories where id=1;" --> New Information Gathered

With chain request we can provide the best output for the user which is our goal

**Important notes:**

1. Do not try to provide multiple queries in single chat response because we will already provide the overall data in the new context
2. Always decide the new query based on the information you got from previous outputs. For instance, don't try to fetch data for all
product_id=1 for all tables because maybe some tables don't contain product_id detail
3. Sometimes, in data there won't be element_id but it doesn't mean our all data fetches are ended. Always check table names for useful
data which can provide information about current request. For instance, orderdetails table can provide information for orders table.

**Output Format:**
Use this JSON schema:

Response = {'is_sql_query': bool, 'content': str}
Return: Response
"""

model = genai.GenerativeModel(model_name='gemini-1.5-flash-latest',
                                           generation_config=generation_config,
                                           safety_settings={
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT : HarmBlockThreshold.BLOCK_NONE,
    },
                                           system_instruction=system_prompt)
chat = model.start_chat(history=[])


import sqlite3
from google.colab import files

# Assume the uploaded file is 'my_database.sqlite'
db_file = '/content/northwind_small.sqlite'

# Connect to the uploaded SQLite database
conn = sqlite3.connect(db_file)
cursor = conn.cursor()
cursor.execute('SELECT * FROM Customers')
tables = cursor.fetchall()

# Print the tables in the database
for table in tables:
    print(table)

# Close the connection
conn.close()


def input_chat(customer_message, previous_data=None):
    # Send the initial customer message to the model
    response = chat.send_message(customer_message)

    # Convert the response JSON into a dictionary
    decision = json.loads(response.text)
    content = decision['content']

    # Now that we have a sufficiently confident answer, return the content (SQL query)
    if decision["is_sql_query"]:
      conn = sqlite3.connect(db_file)
      cursor = conn.cursor()
      print(content)
      cursor.execute(content)
      results = cursor.fetchall()
      only_data = ""
      result_str = "Current overall result is '"
      if previous_data is not None:
        result_str += f"\n{previous_data}\n"
        only_data = previous_data
      for row in results:
          result_str += str(row) + "\n"
          only_data += str(row) + "\n"
      result_str += "'"
      print(result_str)
      return input_chat(result_str, only_data)
    else:
      return content


import gradio as gr
import json


def chatbot_interface(user_input, history):
    return input_chat(user_input)

# Create the Gradio interface
iface = gr.ChatInterface(
    fn=chatbot_interface,
    title="Company Database Chatbot",
    description="Ask questions about the company database, and the chatbot will generate the corresponding SQL query, retrieve the results, and explain them in natural language.",
    type="messages"
)

# Launch the Gradio interface
iface.launch(debug=True)
