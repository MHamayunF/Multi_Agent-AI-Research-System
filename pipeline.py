from agents import (
    build_reader_agent,
    build_search_agent,
    writer_chain,
    critic_chain,
)


def to_text(content) -> str:
    """Gemini may return a string or a list of content blocks; normalise to str."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "\n".join(parts)
    return str(content)


def stream_research_pipeline(topic: str):
    """
    Runs the pipeline step by step and yields (step, phase, state) events:
      step  : "search" | "reader" | "writer" | "critic"
      phase : "start" | "done"
      state : dict of everything produced so far
    """
    state = {}

    # Step 1: Search agent
    yield "search", "start", state
    search_agent = build_search_agent()
    search_result = search_agent.invoke({
        "messages": [
            ("user", f"Find recent, reliable and detailed information about: {topic}")
        ]
    })
    state["search_results"] = to_text(search_result["messages"][-1].content)
    yield "search", "done", state

    # Step 2: Reader agent
    yield "reader", "start", state
    reader_agent = build_reader_agent()
    reader_result = reader_agent.invoke({
        "messages": [
            (
                "user",
                f"Based on the following search results about '{topic}', "
                f"pick the most relevant URL and scrape it for deeper content.\n\n"
                f"Search Results:\n{state['search_results'][:800]}"
            )
        ]
    })
    state["scraped_content"] = to_text(reader_result["messages"][-1].content)
    yield "reader", "done", state

    # Step 3: Writer creates the report
    yield "writer", "start", state
    research_combined = (
        f"SEARCH RESULTS:\n{state['search_results']}\n\n"
        f"DETAILED SCRAPED CONTENT:\n{state['scraped_content']}"
    )
    state["report"] = writer_chain.invoke({
        "topic": topic,
        "research": research_combined
    })
    yield "writer", "done", state

    # Step 4: Critic reviews the report
    yield "critic", "start", state
    state["feedback"] = critic_chain.invoke({"report": state["report"]})
    yield "critic", "done", state


def run_research_pipeline(topic: str) -> dict:
    """Terminal version: same pipeline, with printing."""
    titles = {
        "search": "Step 1 - Search agent is working...",
        "reader": "Step 2 - Reader agent is working...",
        "writer": "Step 3 - Writer is drafting the report...",
        "critic": "Step 4 - Critic is reviewing the report...",
    }
    outputs = {
        "search": ("Search results obtained:", "search_results"),
        "reader": ("Scraped content:", "scraped_content"),
        "writer": ("\nFinal Report:\n", "report"),
        "critic": ("\nCritic Report:\n", "feedback"),
    }

    state = {}
    for step, phase, state in stream_research_pipeline(topic):
        if phase == "start":
            print("\n" + "=" * 50)
            print(titles[step])
            print("=" * 50)
        else:
            label, key = outputs[step]
            print(label)
            print(state[key])
    return state


if __name__ == "__main__":
    topic = input("\nEnter a research topic: ").strip()

    if topic:
        run_research_pipeline(topic)
    else:
        print("Please enter a research topic.")