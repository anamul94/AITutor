from app.core.llm_providers import get_llm_client


def main() -> None:
    llm, llm_context = get_llm_client()
    response = llm.invoke("Who are you?")
    print("Provider:", llm_context.get("provider"))
    print("Configured model:", llm_context.get("configured_model"))
    print(response)


if __name__ == "__main__":
    main()
