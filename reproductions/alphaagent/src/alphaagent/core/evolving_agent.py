from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from tqdm import tqdm

if TYPE_CHECKING:
    from alphaagent.core.evaluation import Evaluator
    from alphaagent.core.evolving_framework import EvolvableSubjects

from alphaagent.core.evaluation import Feedback
from alphaagent.core.evolving_framework import EvolvingStrategy, EvoStep
from alphaagent.log import logger


class EvoAgent(ABC):
    def __init__(self, max_loop: int, evolving_strategy: EvolvingStrategy) -> None:
        self.max_loop = max_loop
        self.evolving_strategy = evolving_strategy

    @abstractmethod
    def multistep_evolve(
        self,
        evo: EvolvableSubjects,
        eva: Evaluator | Feedback,
        filter_final_evo: bool = False,
    ) -> EvolvableSubjects: ...

    @abstractmethod
    def filter_evolvable_subjects_by_feedback(
        self,
        evo: EvolvableSubjects,
        feedback: Feedback | None,
    ) -> EvolvableSubjects: ...


class RAGEvoAgent(EvoAgent):
    def __init__(
        self,
        max_loop: int,
        evolving_strategy: EvolvingStrategy,
        rag: Any,
        with_knowledge: bool = False,
        with_feedback: bool = True,
        knowledge_self_gen: bool = False,
    ) -> None:
        super().__init__(max_loop, evolving_strategy)
        self.rag = rag
        self.evolving_trace: list[EvoStep] = []
        self.with_knowledge = with_knowledge
        self.with_feedback = with_feedback
        self.knowledge_self_gen = knowledge_self_gen

    def multistep_evolve(
        self,
        evo: EvolvableSubjects,
        eva: Evaluator | Feedback,
        filter_final_evo: bool = False,
    ) -> EvolvableSubjects:
        """Multi-step evolution method implementing the full evolution loop
        
        Args:
            evo (EvolvableSubjects): evolvable subject objects
            eva (Evaluator | Feedback): evaluator or feedback object
            filter_final_evo (bool, optional): whether to filter evolvable subjects in the final result. Defaults to False.
            
        Returns:
            EvolvableSubjects: evolved subject objects
            
        The evolution flow contains these steps:
        1. Knowledge self-evolution: if enabled, generate new knowledge from the evolution trace
        2. RAG query: if enabled, retrieve relevant knowledge with RAG
        3. Evolution: evolve subjects with the evolution strategy
        4. Package evolution results: package evolution results and queried knowledge
        5. Evaluation: if feedback is enabled, evaluate evolution results
        6. Update trace: add this evolution step to the evolution trace
        """
        for _ in tqdm(range(self.max_loop), "Debugging"):
            # 1. Knowledge self-evolution: if self-generation and RAG are enabled, generate new knowledge from the evolution trace
            if self.knowledge_self_gen and self.rag is not None:
                self.rag.generate_knowledge(self.evolving_trace)
                
            # 2. RAG query: if knowledge retrieval and RAG are enabled, query relevant knowledge
            queried_knowledge = None
            if self.with_knowledge and self.rag is not None:
                # TODO: Putting the evolution trace here does not actually work
                queried_knowledge = self.rag.query(evo, self.evolving_trace)

            # 3. Evolution: evolve subjects with the evolution strategy
            evo = self.evolving_strategy.evolve(
                evo=evo,
                evolving_trace=self.evolving_trace,
                queried_knowledge=queried_knowledge,
            )
            
            # Record the evolved code workspace
            # TODO: Ignore this mypy error because of the current design
            logger.log_object(evo.sub_workspace_list, tag="evolving code")  # type: ignore[attr-defined]
            for sw in evo.sub_workspace_list:  # type: ignore[attr-defined]
                logger.info(f"evolving code workspace: {sw}")

            # 4. Package evolution results: package results and queried knowledge into an evolution step
            es = EvoStep(evo, queried_knowledge)

            # 5. Evaluation: if feedback is enabled, evaluate the evolution results
            if self.with_feedback:
                es.feedback = (
                    # TODO: Because of the irregular design of rdagent.core.evaluation.Evaluator,
                    # this does not pass mypy for now, so ignore this error temporarily
                    eva
                    if isinstance(eva, Feedback)
                    else eva.evaluate(evo, queried_knowledge=queried_knowledge)  # type: ignore[arg-type, call-arg]
                )
                logger.log_object(es.feedback, tag="evolving feedback")

            # 6. Update trace: add this evolution step to the evolution trace
            self.evolving_trace.append(es)
            
        # If feedback is enabled and filtering is requested, filter evolvable subjects based on the latest feedback
        if self.with_feedback and filter_final_evo:
            evo = self.filter_evolvable_subjects_by_feedback(evo, self.evolving_trace[-1].feedback)
        return evo

    def filter_evolvable_subjects_by_feedback(
        self,
        evo: EvolvableSubjects,
        feedback: Feedback | None,
    ) -> EvolvableSubjects:
        # Implementation of filter_evolvable_subjects_by_feedback method
        pass
