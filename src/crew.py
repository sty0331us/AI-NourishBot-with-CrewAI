"""CrewAI multi-agent crews for recipe suggestion and nutrient analysis."""

from __future__ import annotations

import os
from typing import Optional

import yaml
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

from src.models import NutrientAnalysisOutput, RecipeSuggestionOutput
from src.tools import (
    DietaryFilterTool,
    ExtractIngredientsTool,
    FilterIngredientsTool,
    NutrientAnalysisTool,
)

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")


@CrewBase
class BaseNourishBotCrew:
    """Shared agents and tasks for NourishBot workflows."""

    agents_config_path = os.path.join(CONFIG_DIR, "agents.yaml")
    tasks_config_path = os.path.join(CONFIG_DIR, "tasks.yaml")

    def __init__(
        self, image_data: str, dietary_restrictions: Optional[str] = None
    ) -> None:
        self.image_data = image_data
        self.dietary_restrictions = dietary_restrictions or ""

        with open(self.agents_config_path, "r", encoding="utf-8") as f:
            self.agents_config = yaml.safe_load(f)

        with open(self.tasks_config_path, "r", encoding="utf-8") as f:
            self.tasks_config = yaml.safe_load(f)

    @agent
    def ingredient_detection_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["ingredient_detection_agent"],
            tools=[
                ExtractIngredientsTool.extract_ingredient,
                FilterIngredientsTool.filter_ingredients,
            ],
            allow_delegation=False,
            max_iter=5,
            verbose=True,
        )

    @agent
    def dietary_filtering_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["dietary_filtering_agent"],
            tools=[DietaryFilterTool.filter_based_on_restrictions],
            allow_delegation=True,
            max_iter=6,
            verbose=True,
        )

    @agent
    def nutrient_analysis_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["nutrient_analysis_agent"],
            tools=[NutrientAnalysisTool.analyze_image],
            allow_delegation=False,
            max_iter=4,
            verbose=True,
        )

    @agent
    def recipe_suggestion_agent(self) -> Agent:
        return Agent(
            config=self.agents_config["recipe_suggestion_agent"],
            allow_delegation=False,
            verbose=True,
        )

    @task
    def ingredient_detection_task(self) -> Task:
        task_config = self.tasks_config["ingredient_detection_task"]
        return Task(
            description=task_config["description"],
            agent=self.ingredient_detection_agent(),
            expected_output=task_config["expected_output"],
        )

    @task
    def dietary_filtering_task(self) -> Task:
        task_config = self.tasks_config["dietary_filtering_task"]
        return Task(
            description=task_config["description"],
            agent=self.dietary_filtering_agent(),
            context=[self.ingredient_detection_task()],
            expected_output=task_config["expected_output"],
        )

    @task
    def nutrient_analysis_task(self) -> Task:
        task_config = self.tasks_config["nutrient_analysis_task"]
        return Task(
            description=task_config["description"],
            agent=self.nutrient_analysis_agent(),
            expected_output=task_config["expected_output"],
            output_json=NutrientAnalysisOutput,
        )

    @task
    def recipe_suggestion_task(self) -> Task:
        task_config = self.tasks_config["recipe_suggestion_task"]
        return Task(
            description=task_config["description"],
            agent=self.recipe_suggestion_agent(),
            context=[self.dietary_filtering_task()],
            expected_output=task_config["expected_output"],
            output_json=RecipeSuggestionOutput,
        )


@CrewBase
class NourishBotRecipeCrew(BaseNourishBotCrew):
    """Sequential crew: detect → filter → suggest recipes."""

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[
                self.ingredient_detection_agent(),
                self.dietary_filtering_agent(),
                self.recipe_suggestion_agent(),
            ],
            tasks=[
                self.ingredient_detection_task(),
                self.dietary_filtering_task(),
                self.recipe_suggestion_task(),
            ],
            process=Process.sequential,
            verbose=True,
        )


@CrewBase
class NourishBotAnalysisCrew(BaseNourishBotCrew):
    """Sequential crew: nutrient analysis of a plated dish."""

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.nutrient_analysis_agent()],
            tasks=[self.nutrient_analysis_task()],
            process=Process.sequential,
            verbose=True,
        )
