from langfuse import get_client

langfuse = get_client()

# Create a span using a context manager
with langfuse.start_as_current_observation(as_type="span", name="process-request") as span:
    # Your processing logic here
    span.update(output="Processing complete")

    # Create a nested generation for an LLM call
    with langfuse.start_as_current_observation(as_type="generation", name="llm-response", model="gpt-3.5-turbo") as generation:
        # Your LLM call logic here
        generation.update(output="Generated response")

# All spans are automatically closed when exiting their context blocks

print("test")

# Flush events in short-lived applications
langfuse.flush()
