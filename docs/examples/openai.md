# OpenAI API Key

With OpenAI, you're instructed to [use an API key](https://github.com/openai/openai-python#usage) to authenticate with their APIs. When you put that string in a `.env` file, or directly in your code, you risk sharing your API key with the world! 🙅‍♂️

Instead, just put it in your OS keyring, and expose it with keycmd when you run your Python scripts or Jupyter notebooks.

## Configuration

Add the key to your OS keyring — see the [quick start](../getting-started/quick-start.md#1-store-a-credential-in-your-keyring) for how to do that on each platform. Say you store it under the name `my-openai-token` with username `your-username`; then this is the `.keycmd` configuration you need:

```toml
[keys]
OPENAI_API_KEY = { credential = "my-openai-token", username = "your-username" }
```

`OPENAI_API_KEY` is the variable the OpenAI SDK reads by default, so nothing in your code has to change.

## Usage

Now you can run any OpenAI script by just prefixing your command with `keycmd`:

```bash
keycmd 'python my_openai_script.py'
```

Or a Jupyter notebook:

```bash
keycmd 'jupyter notebook'
```

That's all! 🤘 Now you can rest easily, knowing your tokens are safe. 🛌💤

!!! tip "The same trick works for any SDK"

    Anthropic's `ANTHROPIC_API_KEY`, AWS's `AWS_SECRET_ACCESS_KEY`, a Hugging Face `HF_TOKEN` — anything that reads a credential from the environment is a one-line entry under `[keys]`.
