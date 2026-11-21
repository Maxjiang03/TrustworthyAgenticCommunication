# Model identifiers, parameters and weights

The model-driven experiments use DeepSeek's hosted chat-completions API at `https://api.deepseek.com/chat/completions`. The manuscript names the service used as DeepSeek V4.1 Flash. Archived requests specify `deepseek-v4-flash`; archived responses report `deepseek-flash`. Both identifiers are preserved in the records.

- Temperature: 0.2.
- Thinking: disabled.
- Maximum turns per task: six.
- Configurations: B0, task-scoped exchange, B3.
- Contexts per evaluation: clean input and four fixed injections.
- Repetitions: three per context and configuration, giving 45 task runs.
- Follow-up selection: 11 B0 development trials, then a frozen payload selection and a separate 45-run evaluation.

The project performs no model training or fine-tuning and uses no local model weights. Consequently, there is no weight file to download or redistribute. Provider weights remain hosted by the provider. Prompts, tool definitions, raw responses, call traces and scoring code are included for offline result reconstruction.

For new live runs, supply your own key through `DEEPSEEK_API_KEY` or the runner's hidden prompt. Never place it in a source file, command argument, result file, or commit. New responses retain the requested and returned model identifiers so that provider routing changes remain visible.

Offline reconstruction uses only the archived responses and makes no network calls to the model service.
