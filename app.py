"""Gradio web application for AI NourishBot."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import gradio as gr
from dotenv import load_dotenv

from src.crew import NourishBotAnalysisCrew, NourishBotRecipeCrew

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


def format_recipe_output(final_output: dict[str, Any]) -> str:
    """Format the recipe workflow output as Markdown tables."""
    output = "## Recipe Ideas\n\n"
    recipes: list[dict[str, Any]] = []

    if "recipes" in final_output:
        recipes = final_output["recipes"]
    else:
        recipe_task_output = final_output.get("recipe_suggestion_task")
        if (
            recipe_task_output
            and hasattr(recipe_task_output, "json_dict")
            and recipe_task_output.json_dict
        ):
            recipes = recipe_task_output.json_dict.get("recipes", [])

    if not recipes:
        return output + "No recipes could be generated."

    for idx, recipe in enumerate(recipes, 1):
        output += f"### {idx}. {recipe['title']}\n\n"
        output += "**Ingredients:**\n"
        output += "| Ingredient |\n"
        output += "|------------|\n"
        for ingredient in recipe["ingredients"]:
            output += f"| {ingredient} |\n"
        output += "\n"
        output += f"**Instructions:**\n{recipe['instructions']}\n\n"
        output += f"**Calorie Estimate:** {recipe['calorie_estimate']} kcal\n\n"
        output += "---\n\n"

    return output


def format_analysis_output(final_output: dict[str, Any]) -> str:
    """Format the nutritional analysis workflow output as Markdown tables."""
    output = "## Nutritional Analysis\n\n"

    if dish := final_output.get("dish"):
        output += f"**Dish:** {dish}\n\n"
    if portion := final_output.get("portion_size"):
        output += f"**Portion Size:** {portion}\n\n"
    if est_cal := final_output.get("estimated_calories"):
        output += f"**Estimated Calories:** {est_cal} calories\n\n"
    if total_cal := final_output.get("total_calories"):
        output += f"**Total Calories:** {total_cal} calories\n\n"

    output += "**Nutrient Breakdown:**\n\n"
    output += "| **Nutrient**       | **Amount** |\n"
    output += "|--------------------|------------|\n"

    nutrients = final_output.get("nutrients", {}) or {}
    for macro in ["protein", "carbohydrates", "fats"]:
        if value := nutrients.get(macro):
            output += f"| **{macro.capitalize()}** | {value} |\n"

    vitamins = nutrients.get("vitamins", []) or []
    if vitamins:
        output += "\n**Vitamins:**\n\n"
        output += "| **Vitamin** | **%DV** |\n"
        output += "|-------------|--------|\n"
        for vitamin in vitamins:
            name = vitamin.get("name", "N/A")
            dv = vitamin.get("percentage_dv", "N/A")
            output += f"| {name} | {dv} |\n"

    minerals = nutrients.get("minerals", []) or []
    if minerals:
        output += "\n**Minerals:**\n\n"
        output += "| **Mineral** | **Amount** |\n"
        output += "|-------------|-----------|\n"
        for mineral in minerals:
            name = mineral.get("name", "N/A")
            amount = mineral.get("amount", "N/A")
            output += f"| {name} | {amount} |\n"

    if health_eval := final_output.get("health_evaluation"):
        output += "\n**Health Evaluation:**\n\n"
        output += health_eval + "\n"

    return output


def analyze_food(
    image,
    dietary_restrictions: str,
    workflow_type: str,
    progress=gr.Progress(track_tqdm=True),
) -> str:
    """Run the selected NourishBot crew workflow and return Markdown results."""
    if image is None:
        return "Please upload an image before analyzing."

    if workflow_type not in {"recipe", "analysis"}:
        return "Invalid workflow type. Choose 'recipe' or 'analysis'."

    with tempfile.NamedTemporaryFile(
        suffix=".jpg", delete=False, dir=UPLOADS_DIR
    ) as tmp:
        image_path = tmp.name
        image.save(image_path)

    inputs = {
        "uploaded_image": image_path,
        "dietary_restrictions": dietary_restrictions or "",
        "workflow_type": workflow_type,
    }

    try:
        progress(0.1, desc="Initializing crew…")
        if workflow_type == "recipe":
            crew_instance = NourishBotRecipeCrew(
                image_data=image_path,
                dietary_restrictions=dietary_restrictions or "",
            )
        else:
            crew_instance = NourishBotAnalysisCrew(image_data=image_path)

        progress(0.3, desc=f"Running {workflow_type} workflow…")
        crew_obj = crew_instance.crew()
        result = crew_obj.kickoff(inputs=inputs)
        final_output = result.to_dict() if hasattr(result, "to_dict") else dict(result)

        progress(0.9, desc="Formatting results…")
        if workflow_type == "recipe":
            return format_recipe_output(final_output)
        return format_analysis_output(final_output)

    except Exception as exc:  # noqa: BLE001 — surface errors in the UI
        logger.exception("Workflow failed")
        return f"**Error:** {exc}"
    finally:
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except OSError:
                logger.warning("Could not remove temp image: %s", image_path)


CSS = """
.title {
    font-size: 1.5em !important;
    text-align: center !important;
    color: #FFD700;
}
.text {
    text-align: center;
}
"""

JS = """
function createGradioAnimation() {
    var container = document.createElement('div');
    container.id = 'gradio-animation';
    container.style.fontSize = '2em';
    container.style.fontWeight = 'bold';
    container.style.textAlign = 'center';
    container.style.marginBottom = '20px';
    container.style.color = '#eba93f';

    var text = 'Welcome to your AI NourishBot!';
    for (var i = 0; i < text.length; i++) {
        (function(i){
            setTimeout(function(){
                var letter = document.createElement('span');
                letter.style.opacity = '0';
                letter.style.transition = 'opacity 0.1s';
                letter.innerText = text[i];
                container.appendChild(letter);
                setTimeout(function() { letter.style.opacity = '0.9'; }, 50);
            }, i * 250);
        })(i);
    }

    var gradioContainer = document.querySelector('.gradio-container');
    if (gradioContainer) {
        gradioContainer.insertBefore(container, gradioContainer.firstChild);
    }
    return 'Animation created';
}
"""

EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"
EXAMPLE_PATHS = [
    [str(EXAMPLES_DIR / "food-1.jpg"), "vegan", "recipe"],
    [str(EXAMPLES_DIR / "food-2.jpg"), "", "analysis"],
    [str(EXAMPLES_DIR / "food-3.jpg"), "keto", "recipe"],
    [str(EXAMPLES_DIR / "food-4.jpg"), "", "analysis"],
]
AVAILABLE_EXAMPLES = [
    ex for ex in EXAMPLE_PATHS if Path(ex[0]).exists()
]


with gr.Blocks(theme=gr.themes.Citrus(), css=CSS, js=JS) as demo:
    gr.Markdown("# How it works", elem_classes="title")
    gr.Markdown(
        "Upload an image of your fridge content, enter your dietary restriction "
        "(if any), select workflow type **recipe**, then click **Analyze** for recipe ideas.",
        elem_classes="text",
    )
    gr.Markdown(
        "Upload an image of a complete dish, leave dietary restriction blank, "
        "select workflow type **analysis**, then click **Analyze** for nutritional insights.",
        elem_classes="text",
    )
    gr.Markdown(
        "You can also select one of the examples provided to autofill the inputs "
        "and click **Analyze** right away!",
        elem_classes="text",
    )

    with gr.Row():
        with gr.Column(scale=1, min_width=400):
            gr.Markdown("## Inputs", elem_classes="title")
            image_input = gr.Image(type="pil", label="Upload Image")
            dietary_input = gr.Textbox(
                label="Dietary Restrictions (optional)",
                placeholder="e.g., vegan, keto, gluten-free",
            )
            workflow_radio = gr.Radio(
                ["recipe", "analysis"], label="Workflow Type", value="recipe"
            )
            submit_btn = gr.Button("Analyze", variant="primary")

        with gr.Column(scale=2, min_width=600):
            if AVAILABLE_EXAMPLES:
                gr.Examples(
                    examples=AVAILABLE_EXAMPLES,
                    inputs=[image_input, dietary_input, workflow_radio],
                    label="Try an Example: select one below to autofill, then click Analyze",
                )
            gr.Markdown("## Results will appear here...", elem_classes="title")
            result_display = gr.Markdown(
                "<div style='border: 1px solid #ccc; padding: 1rem; "
                "text-align: center; color: #666;'>No results yet</div>",
                height=500,
            )

    submit_btn.click(
        fn=analyze_food,
        inputs=[image_input, dietary_input, workflow_radio],
        outputs=result_display,
    )


if __name__ == "__main__":
    server_name = os.getenv("GRADIO_SERVER_NAME", "127.0.0.1")
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "5000"))
    demo.launch(server_name=server_name, server_port=server_port)
