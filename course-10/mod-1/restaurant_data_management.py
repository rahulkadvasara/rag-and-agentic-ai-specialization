from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional
import json
import os
import shutil
import io
import unittest
from unittest.mock import patch


FILEPATH = 'structured_restaurant_data.json'
BACKUP_PATH = 'structured_restaurant_data.json.bak'

EXAMPLE_RESTAURANT_PARAGRAPH = (
    'Down in **Santa Monica**, **Mar de Cortez** serves as a '
    '**sun-drenched**, **casual taqueria** specializing in **Baja-style '
    'seafood**. With a **4.2/5** rating, it captures the salt-air energy '
    'of the coast through its signature beer-battered snapper tacos and '
    'zesty octopus ceviche, making it a premier spot for open-air dining '
    'near the pier. Price range: $$'
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def load_data(file_path):
    """
    Load restaurant data from the JSON file.
    If the file does not exist, return an empty list.
    """
    if not os.path.exists(file_path):
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_data(file_path, data, backup_path):
    """
    Save restaurant data to JSON.
    Create a backup of the existing file before saving.
    """

    # Create backup if the original file exists
    if os.path.exists(file_path):
        shutil.copy2(file_path, backup_path)

    # Save the updated data
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def show_restaurant_card(data, index):
    """
    Display the detailed information for one restaurant.
    """
    restaurant = data[index]

    print("\n--- Restaurant Details ---")

    for key, value in restaurant.items():
        print(f"{key}: {value}")


# ============================================================
# EXERCISE 1
# INTEGRATE THE LLM MODEL FROM LESSON 1
# ============================================================

def restaurant_data_structure_prompt_generation(restaurant_paragraph):
    """
    Generate the prompt used to convert an unstructured
    restaurant paragraph into structured JSON.
    """

    prompt = f"""
You are an expert restaurant data extraction assistant.

Convert the following unstructured restaurant description
into a structured JSON object.

Restaurant description:
{restaurant_paragraph}

Return ONLY valid JSON.
Do not include markdown code fences.
Do not include explanations or additional text.

Extract all useful restaurant information available in
the description.

Include fields such as:
- name
- location
- description
- cuisine
- rating
- price
- features

If a field is not available, use null.

Restaurant description:
{restaurant_paragraph}
"""

    return prompt


def llm_model(system_msg, prompt_txt):
    """
    Call the IBM Granite model defined in Lesson 1.
    """

    # Same model configuration as Lesson 1
    model_id = "ibm/granite-4-h-small"

    project_id = "skills-network"

    credentials = Credentials(
        url="https://us-south.ml.cloud.ibm.com"
    )

    # Define the model
    model = ModelInference(
        model_id=model_id,
        credentials=credentials,
        project_id=project_id
    )

    # Define messages
    messages = [
        {
            "role": "system",
            "content": system_msg
        },
        {
            "role": "user",
            "content": prompt_txt
        }
    ]

    # Get the response
    response = model.chat(messages=messages)

    output_text = response["choices"][0]["message"]["content"]

    return output_text


def JSON_auto_repair_prompts(response, error_message):
    """
    Generate a prompt asking the LLM to repair invalid JSON.
    """

    prompt = f"""
The following response was supposed to be valid JSON,
but it could not be parsed.

Original response:
{response}

JSON parsing error:
{error_message}

Please repair the response.

Return ONLY valid JSON.
Do not include markdown code fences.
Do not include explanations.
"""

    return prompt


def new_data_entry_process(paragraph, itemId):
    """
    Convert a raw restaurant paragraph into structured JSON
    using the IBM Granite model.
    """

    system_msg = """
You are a restaurant data structuring assistant.

Your task is to convert an unstructured restaurant
description into a structured JSON object.

Always return exactly one valid JSON object.
Do not return markdown.
Do not return explanations.
"""

    # Generate the structuring prompt
    prompt = restaurant_data_structure_prompt_generation(
        paragraph
    )

    # Call the LLM
    response = llm_model(
        system_msg,
        prompt
    )

    response = response.strip()

    # Remove markdown code fences if the model returned them
    if response.startswith("```json"):
        response = response[7:]

    elif response.startswith("```"):
        response = response[3:]

    if response.endswith("```"):
        response = response[:-3]

    response = response.strip()

    # Try to parse the response as JSON
    try:
        restaurant_data = json.loads(response)

    except json.JSONDecodeError as error:

        # Ask the LLM to repair the JSON
        repair_prompt = JSON_auto_repair_prompts(
            response,
            str(error)
        )

        repaired_response = llm_model(
            system_msg,
            repair_prompt
        )

        repaired_response = repaired_response.strip()

        # Remove markdown code fences
        if repaired_response.startswith("```json"):
            repaired_response = repaired_response[7:]

        elif repaired_response.startswith("```"):
            repaired_response = repaired_response[3:]

        if repaired_response.endswith("```"):
            repaired_response = repaired_response[:-3]

        repaired_response = repaired_response.strip()

        # Parse repaired JSON
        restaurant_data = json.loads(
            repaired_response
        )

    # Add the item ID
    restaurant_data["itemId"] = itemId

    return restaurant_data


# ============================================================
# EXERCISE 2
# MAIN UI FUNCTION
# ============================================================

def manage_restaurants(
    file_path=FILEPATH,
    backup_path=BACKUP_PATH
):

    while True:

        # Load current database
        data = load_data(file_path)

        print(
            f"\n🏨 RESTAURANT DATABASE | Records: {len(data)}"
        )

        print("1. Browse All (Names)")
        print("2. View Detailed Record")
        print("3. Add New Restaurant")
        print("4. Edit Restaurant Info")
        print("5. Delete Restaurant")
        print("6. Exit")

        choice = input("\nAction: ")

        # ----------------------------------------------------
        # OPTION 1: BROWSE NAMES
        # ----------------------------------------------------

        if choice == '1':

            print("\n--- Current Listings ---")

            for restaurant in data:
                print(
                    restaurant.get("name", "N/A")
                )

        # ----------------------------------------------------
        # OPTION 2: VIEW DETAILED RECORD
        # ----------------------------------------------------

        elif choice == '2':

            try:
                index = int(
                    input("Enter record index: ")
                )

                if 0 <= index < len(data):
                    show_restaurant_card(
                        data,
                        index
                    )
                else:
                    print("invalid index.")

            except ValueError:
                print("invalid index.")

        # ----------------------------------------------------
        # OPTIONS 3, 4, 5: WRITE OPERATIONS
        # ----------------------------------------------------

        elif choice in ['3', '4', '5']:

            # Security warning
            print(
                "\n❗ SECURITY WARNING: "
                "You are entering write-mode."
            )

            print(
                "Changes will be saved to the database immediately."
            )

            confirm = input(
                "Are you sure? "
                "(type 'yes' to proceed): "
            ).lower()

            if confirm != 'yes':

                print("Operation cancelled.")
                continue

            # ------------------------------------------------
            # OPTION 3: ADD NEW RESTAURANT
            # ------------------------------------------------

            if choice == '3':

                # Generate item ID
                itemId = 1000000 + len(data) + 1

                # Ask for raw restaurant paragraph
                paragraph = input(
                    "\nEnter the new restaurant description:\n"
                )

                # Process using the LLM
                new_restaurant = new_data_entry_process(
                    paragraph,
                    itemId
                )

                # Add to database
                data.append(new_restaurant)

                # Save
                save_data(
                    file_path,
                    data,
                    backup_path
                )

                print("✅ Restaurant added.")

            # ------------------------------------------------
            # OPTION 4: EDIT RESTAURANT
            # ------------------------------------------------

            elif choice == '4':

                try:

                    index = int(
                        input(
                            "Enter record index to edit: "
                        )
                    )

                    if 0 <= index < len(data):

                        # Make a list of keys so that
                        # dictionary changes are safe
                        keys = list(
                            data[index].keys()
                        )

                        for key in keys:

                            current_value = data[index][key]

                            new_value = input(
                                f"{key} [{current_value}]: "
                            )

                            # Empty input means:
                            # keep the current value
                            if new_value.strip() != "":
                                data[index][key] = new_value

                        # Save changes
                        save_data(
                            file_path,
                            data,
                            backup_path
                        )

                        print("✅ Record updated.")

                    else:
                        print("invalid index.")

                except ValueError:
                    print("invalid index.")

            # ------------------------------------------------
            # OPTION 5: DELETE RESTAURANT
            # ------------------------------------------------

            elif choice == '5':

                try:

                    index = int(
                        input(
                            "Enter record index to delete: "
                        )
                    )

                    if 0 <= index < len(data):

                        # Delete restaurant
                        data.pop(index)

                        # Save changes
                        save_data(
                            file_path,
                            data,
                            backup_path
                        )

                        print("✅ Record deleted.")

                    else:
                        print("invalid index.")

                except ValueError:
                    print("invalid index.")

        # ----------------------------------------------------
        # OPTION 6: EXIT
        # ----------------------------------------------------

        elif choice == '6':

            break

        # ----------------------------------------------------
        # INVALID OPTION
        # ----------------------------------------------------

        else:

            print("Invalid input.")


# ============================================================
# EXERCISE 3
# UNIT TESTS
# ============================================================

class TestRestaurantDatabase(unittest.TestCase):

    def setUp(self):
        """
        Create a temporary clean database for testing.
        """

        self.test_file = (
            'structured_restaurant_data_unit_test.json'
        )

        self.test_file_backup = (
            'structured_restaurant_data_unit_test.json.bak'
        )

        self.initial_data = [
            {
                "name": "Test Cafe",
                "location": "Test City"
            }
        ]

        with open(
            self.test_file,
            'w',
            encoding='utf-8'
        ) as f:

            json.dump(
                self.initial_data,
                f
            )

    def tearDown(self):
        """
        Clean up the test files after tests.
        """

        if os.path.exists(self.test_file):
            os.remove(self.test_file)

        if os.path.exists(self.test_file_backup):
            os.remove(self.test_file_backup)

    @patch('builtins.input')
    @patch(
        'sys.stdout',
        new_callable=io.StringIO
    )
    def test_add_and_delete_restaurant_success(
        self,
        mock_stdout,
        mock_input
    ):
        """
        Test:
        1. Add restaurant.
        2. Delete restaurant.
        """

        mock_restaurant = (
            'The Copper Sprout is a high-concept, '
            'Modern Appalachian farm-to-table destination '
            'that blends an industrial-chic aesthetic with '
            'rustic forest charm, featuring reclaimed wood '
            'and amber lighting to create a sophisticated '
            'yet cozy vibe. Priced in the $$ category, the '
            'menu celebrates seasonal foraging and local '
            'heritage, headlined by signature dishes like '
            'Cast-Iron Smoked Trout with pickled fiddlehead '
            'ferns and hand-foraged Wild Mushroom Risotto '
            'with aged goat cheese. The experience is '
            'designed to be intimate and earthy, making it '
            'a premier spot for those seeking high-quality, '
            'smokehouse-influenced cuisine in a refined, '
            'atmospheric setting.'
        )

        # Add restaurant
        mock_input.side_effect = [
            '3',
            'yes',
            mock_restaurant,
            '6'
        ]

        try:

            manage_restaurants(
                self.test_file,
                self.test_file_backup
            )

        except SystemExit:
            pass

        # Check saved data
        with open(
            self.test_file,
            'r',
            encoding='utf-8'
        ) as f:

            data = json.load(f)

        self.assertEqual(
            len(data),
            2
        )

        self.assertIn(
            "✅ Restaurant added.",
            mock_stdout.getvalue()
        )

        # Delete restaurant
        mock_input.side_effect = [
            '5',
            'yes',
            '1',
            '6'
        ]

        try:

            manage_restaurants(
                self.test_file,
                self.test_file_backup
            )

        except SystemExit:
            pass

        # Check data after deletion
        with open(
            self.test_file,
            'r',
            encoding='utf-8'
        ) as f:

            data = json.load(f)

        self.assertEqual(
            len(data),
            1
        )

    @patch('builtins.input')
    @patch(
        'sys.stdout',
        new_callable=io.StringIO
    )
    def test_delete_security_cancel(
        self,
        mock_stdout,
        mock_input
    ):
        """
        Test that cancelling a delete operation
        leaves the database unchanged.
        """

        mock_input.side_effect = [
            '5',
            'no',
            '6'
        ]

        manage_restaurants(
            self.test_file,
            self.test_file_backup
        )

        # Check that data remains unchanged
        with open(
            self.test_file,
            'r',
            encoding='utf-8'
        ) as f:

            data = json.load(f)

        self.assertEqual(
            len(data),
            1
        )

        self.assertIn(
            "Operation cancelled.",
            mock_stdout.getvalue()
        )


# ============================================================
# RUN UNIT TESTS
# ============================================================

if __name__ == "__main__":
    # unittest.main()
    manage_restaurants()