"""Opt-in single-inference provider smoke. Run as a module, outside pytest."""

import asyncio
import os
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from pipecat.frames.frames import EndFrame, FunctionCallResultProperties, LLMRunFrame

from backend.clinic import Clinic, clinic_now
from backend.session import Conversation
from backend.voice import (
    PROMPT,
    SPECS,
    GoogleLLMService,
    LLMContext,
    LLMContextAggregatorPair,
    Pipeline,
    PipelineWorker,
    WorkerRunner,
    tool_schema,
)


async def main():
    load_dotenv()
    logger.remove()
    with tempfile.TemporaryDirectory() as folder:
        call = Conversation(Clinic(Path(folder) / "probe.sqlite"))
        llm = GoogleLLMService(
            api_key=os.environ["GEMINI_API_KEY"],
            settings=GoogleLLMService.Settings(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                system_instruction=PROMPT + " Clinic date: " + str(clinic_now().date()),
            ),
        )
        context = LLMContext(
            [
                {
                    "role": "user",
                    "content": "Please check Dr Asha Menon's actual availability tomorrow.",
                }
            ],
            tools=tool_schema(),
        )
        pair = LLMContextAggregatorPair(context)
        worker = PipelineWorker(
            Pipeline([pair.user(), llm, pair.assistant()]), enable_rtvi=False
        )
        result = {}

        async def handle(params):
            print(
                "Lookup arguments:",
                {
                    k: v
                    for k, v in params.arguments.items()
                    if k in {"doctor", "date", "specialty"}
                },
            )
            result.update(
                call.invoke(
                    params.function_name, dict(params.arguments), params.tool_call_id
                )
            )
            print(
                "Gemini invoked",
                params.function_name,
                "; returned",
                len(result.get("slots", [])),
                "slots",
            )
            if result.get("error"):
                print("Service outcome:", result["error"])
            await params.result_callback(
                result, properties=FunctionCallResultProperties(run_llm=False)
            )
            await worker.queue_frame(EndFrame())

        for name, *_ in SPECS:
            llm.register_function(name, handle)

        @worker.event_handler("on_pipeline_started")
        async def start(*_):
            await worker.queue_frame(LLMRunFrame())

        @worker.event_handler("on_pipeline_error")
        async def failed(_, frame):
            import re

            codes = re.findall(
                r"\b(?:400|401|403|404|429|500|503|RESOURCE_EXHAUSTED|PERMISSION_DENIED)\b",
                str(frame.error),
            )
            print("Provider error", ",".join(dict.fromkeys(codes)) or "unclassified")
            await worker.queue_frame(EndFrame())

        runner = WorkerRunner(handle_sigint=False)
        await runner.add_workers(worker)
        await asyncio.wait_for(runner.run(), 45)
        if not result.get("slots"):
            raise SystemExit("Live tool call not verified")


if __name__ == "__main__":
    asyncio.run(main())
