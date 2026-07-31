"""CrewAI tools for ingredient extraction, dietary filtering, and nutrient analysis."""

from __future__ import annotations

import base64
import logging
import os
from io import BytesIO
from typing import List, Optional

import requests
from crewai.tools import tool

from src.watsonx_client import get_text_model, get_vision_model

logger = logging.getLogger(__name__)


def _load_image_as_base64(image_input: str) -> str:
    """Load a local path or remote URL and return a base64-encoded JPEG string."""
    if image_input.startswith("http"):
        response = requests.get(image_input, timeout=30)
        response.raise_for_status()
        image_bytes = BytesIO(response.content)
    else:
        if not os.path.isfile(image_input):
            raise FileNotFoundError(f"No file found at path: {image_input}")
        with open(image_input, "rb") as file:
            image_bytes = BytesIO(file.read())

    return base64.b64encode(image_bytes.read()).decode("utf-8")


class ExtractIngredientsTool:
    @staticmethod
    @tool("Extract ingredients")
    def extract_ingredient(image_input: str) -> str:
        """
        Extract ingredients from a food item image.

        :param image_input: The image file path (local) or URL (remote).
        :return: A list of ingredients extracted from the image.
        """
        logger.info("Extracting ingredients from image: %s", image_input)
        encoded_image = _load_image_as_base64(image_input)
        model = get_vision_model(max_tokens=300)

        response = model.chat(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract ingredients from the food item image. "
                            "Return a comma-separated list of ingredients only.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}"
                            },
                        },
                    ],
                }
            ]
        )
        return response["choices"][0]["message"]["content"]


class FilterIngredientsTool:
    @staticmethod
    @tool("Filter ingredients")
    def filter_ingredients(raw_ingredients: str) -> List[str]:
        """
        Processes the raw ingredient data and filters out non-food items or noise.

        :param raw_ingredients: Raw ingredients as a string.
        :return: A list of cleaned and relevant ingredients.
        """
        ingredients = [
            ingredient.strip().lower()
            for ingredient in raw_ingredients.replace("\n", ",").split(",")
            if ingredient.strip()
        ]
        logger.info("Filtered raw ingredients → %s", ingredients)
        return ingredients


class DietaryFilterTool:
    @staticmethod
    @tool("Filter based on dietary restrictions")
    def filter_based_on_restrictions(
        ingredients: List[str], dietary_restrictions: Optional[str] = None
    ) -> List[str]:
        """
        Uses an LLM model to filter ingredients based on dietary restrictions.

        :param ingredients: List of ingredients.
        :param dietary_restrictions: Dietary restrictions (e.g., vegan, gluten-free).
        :return: Filtered list of ingredients that comply with the dietary restrictions.
        """
        if not dietary_restrictions:
            return ingredients

        model = get_text_model(max_tokens=150)
        prompt = f"""
        You are an AI nutritionist specialized in dietary restrictions.
        Given the following list of ingredients: {', '.join(ingredients)},
        and the dietary restriction: {dietary_restrictions},
        remove any ingredient that does not comply with this restriction.
        Return only the compliant ingredients as a comma-separated list with no additional commentary.
        """

        response = model.chat(
            messages=[
                {
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}],
                }
            ]
        )

        filtered = response["choices"][0]["message"]["content"].strip().lower()
        filtered_list = [item.strip() for item in filtered.split(",") if item.strip()]
        logger.info(
            "Dietary filter (%s): %s → %s",
            dietary_restrictions,
            ingredients,
            filtered_list,
        )
        return filtered_list


NUTRIENT_ANALYSIS_PROMPT = """
You are an expert nutritionist. Your task is to analyze the food items displayed in the image and provide a detailed nutritional assessment using the following format:
1. **Identification**: List each identified food item clearly, one per line.
2. **Portion Size & Calorie Estimation**: For each identified food item, specify the portion size and provide an estimated number of calories. Use bullet points with the following structure:
- **[Food Item]**: [Portion Size], [Number of Calories] calories
Example:
*   **Salmon**: 6 ounces, 210 calories
*   **Asparagus**: 3 spears, 25 calories
3. **Total Calories**: Provide the total number of calories for all food items.
Example:
Total Calories: [Number of Calories]
4. **Nutrient Breakdown**: Include a breakdown of key nutrients such as **Protein**, **Carbohydrates**, **Fats**, **Vitamins**, and **Minerals**. Use bullet points, and for each nutrient provide details about the contribution of each food item.
Example:
*   **Protein**: Salmon (35g), Asparagus (3g), Tomatoes (1g) = [Total Protein]
5. **Health Evaluation**: Evaluate the healthiness of the meal in one paragraph.
6. **Disclaimer**: Include the following exact text as a disclaimer:
The nutritional information and calorie estimates provided are approximate and are based on general food data.
Actual values may vary depending on factors such as portion size, specific ingredients, preparation methods, and individual variations.
For precise dietary advice or medical guidance, consult a qualified nutritionist or healthcare provider.
Format your response exactly like the template above to ensure consistency.
"""


class NutrientAnalysisTool:
    @staticmethod
    @tool("Analyze nutritional values and calories of the dish from uploaded image")
    def analyze_image(image_input: str) -> str:
        """
        Provide a detailed nutrient breakdown and estimate the total calories
        of all ingredients from the uploaded image.

        :param image_input: The image file path (local) or URL (remote).
        :return: A string with nutrient breakdown and estimated calorie information.
        """
        logger.info("Analyzing nutrients from image: %s", image_input)
        encoded_image = _load_image_as_base64(image_input)
        model = get_vision_model(max_tokens=800)

        response = model.chat(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": NUTRIENT_ANALYSIS_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}"
                            },
                        },
                    ],
                }
            ]
        )
        return response["choices"][0]["message"]["content"]
