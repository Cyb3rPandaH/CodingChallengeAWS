# the organization Coding Challenge

By Jose Rodriguez [@Cyb3rPandaH](https://x.com/Cyb3rPandaH)

## Table of Contents

- [Executive Summary](#executive-summary)
- [Infrastructure Required](#infrastructure-required)
- [Virtual Environment Setup](#virtual-environment-setup)
- [Chatbot Application Features](#chatbot-application-features)
  - [Evaluation Set](#evaluation-set)
  - [Evaluation Metrics](#evaluation-metrics)
  - [LLM-as-a-Judge](#llm-as-a-judge)
  - [Execution Tracing](#execution-tracing)
  - [BOTO3-based AWS Tools](#boto3-based-aws-tools)
  - [LLM Tool Execution Rounds](#llm-tool-execution-rounds)
  - [Evaluation Results Output File](#evaluation-results-output-file)
- [Chatbot Application Execution Modes](#chatbot-application-execution-modes)
- [Last Evaluation Results](#last-evaluation-results)
- [Challenges](#challenges)
- [Lessons Learned](#lessons-learned)
- [Next Steps](#next-steps)

## Executive Summary

This project builds and evaluates an AWS security chatbot using a mock AWS environment in Moto, trace storage in PostgreSQL, and an OpenAI model (`gpt-5-mini`) for both answering and judging. The workflow includes environment setup, seed-data creation, interactive chatbot use, and batch evaluation with saved results in `evaluation/last_eval_results.json`.

The chatbot is connected to eight read-focused boto3 tools for S3 and EC2 context, and uses a controlled multi-round tool loop (`MAX_TOOL_ROUNDS`, default `5`) to complete multi-step questions. A tracing module logs session start/end, user input, model outputs, tool calls, and tool results by `trace_id`, which makes behavior easier to inspect and debug.

Evaluation is done in two steps: first generate answers, then run an LLM-as-a-judge pass with correctness and quality scoring (`relevance`, `coherence`, `conciseness`). The latest reported results show strong overall quality and good accuracy, with best performance on comparison questions and higher latency/rounds as complexity increases.

Main challenges included imperfect alignment between ACL and policy status signals in Moto and inconsistent tool-calling behavior when testing some local Ollama model setups. The project moved to `ChatOpenAI` for more stable tool-calling, and future work focuses on better tool-sequence evaluation, token-cost tracking, and support for longer conversations with stronger memory.


---

## Infrastructure Required

### Docker Containers

This project requires two Docker containers: Moto Server and PostgreSQL.

Moto Server is used to run the chatbot application against a persistent mock AWS environment.

PostgreSQL is used to store execution and LLM processing traces for observability and monitoring.

### OpenAI API Key

An OpenAI API key is required to answer questions and evaluate responses.

### Personal Computer & Python Version

This project has been developed and tested using a MacBook Pro (M4 Chip - Tahoe 26.2). The Python version used is `3.12.12`.

---

## Virtual Environment Setup

To run the chatbot application, follow the steps below to set up the environment:

1. Make sure Docker is installed and running on your device.

    ```bash
    docker version
    ```

    ```bash
    jose@joses-MacBook-Pro the organization % docker version
    Client:
    Version:           29.2.0
    API version:       1.53
    Go version:        go1.25.6
    Git commit:        0b9d198
    Built:             Mon Jan 26 19:25:13 2026
    OS/Arch:           darwin/arm64
    Context:           desktop-linux

    Server: Docker Desktop 4.59.1 (217750)
    Engine:
    Version:          29.2.0
    API version:      1.53 (minimum version 1.44)
    Go version:       go1.25.6
    Git commit:       9c62384
    Built:            Mon Jan 26 19:25:48 2026
    OS/Arch:          linux/arm64
    Experimental:     false
    containerd:
    Version:          v2.2.1
    GitCommit:        dea7da592f5d1d2b7755e3a161be07f43fad8f75
    runc:
    Version:          1.3.4
    GitCommit:        v1.3.4-0-gd6d73eb8
    docker-init:
    Version:          0.19.0
    GitCommit:        de40ad0
    ```

2. Add your OpenAI API key to the `.env` file.

    ```
    # OpenAI API Key
    OPENAI_API_KEY=<YOUR_OPENAI_API_KEY_HERE>
    ```

3. Change your current directory to the `the organization` folder.

4. Deploy the containers by running `docker compose up -d`.

5. Verify the containers were created by running `docker ps`. You should see 2 containers.

    ```bash
    docker ps
    ```

    ```bash
    jose@joses-MacBook-Pro the organization % docker ps
    CONTAINER ID   IMAGE                    COMMAND                  CREATED          STATUS          PORTS                                         NAMES
    0b363b30aa5d   postgres:latest          "docker-entrypoint.s…"   13 seconds ago   Up 12 seconds   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp   the-organization-db-1
    fa1a922bb57a   motoserver/moto:latest   "/usr/local/bin/moto…"   13 seconds ago   Up 12 seconds   0.0.0.0:3000->3000/tcp, [::]:3000->3000/tcp   the-organization-motoserver-1
    ```

6. Create and activate a Python virtual environment by running the following commands:

    ```bash
    python -m venv chatbot.venv

    source chatbot.venv/bin/activate
    ```

7. Install Python library requirements by running:

    ```bash
    pip install -r requirements.txt 
    ```

8. Seed AWS mock data on the Moto server. We will use the `seed_data.py` script. Run the following command:

    ```bash
    python scripts/seed_data.py
    ```

    ```bash
    ((chatbot.venv) ) jose@joses-MacBook-Pro the organization % python scripts/seed_data.py 
    Creating IAM user: retail-admin with permissions boundary: arn:aws:iam::aws:policy/ReadOnlyAccess...
    Creating IAM user: retail-dev with permissions boundary: arn:aws:iam::aws:policy/ReadOnlyAccess...
    Creating IAM user: retail-security with permissions boundary: arn:aws:iam::aws:policy/ReadOnlyAccess...
    Creating EC2 instance with image_id: ami-0c55b159cbfafe1f0, instance_type: t3.micro...
    Creating EC2 instance with image_id: ami-0c55b159cbfafe1f0, instance_type: t3.micro...
    Creating S3 bucket: retail-web-assets with ACL: public-read...
    Creating S3 bucket: retail-orders-private with ACL: private...
    Creating S3 bucket: retail-sensitive-public with ACL: public-read-write...
    Creating S3 bucket: retail-security-audit with ACL: private...
    Applying bucket policy to bucket: retail-web-assets...
    Applying bucket policy to bucket: retail-sensitive-public...
    Creating file: site/index.html in bucket: retail-web-assets...
    Creating file: site/app.js in bucket: retail-web-assets...
    Creating file: orders/2026-02-16.json in bucket: retail-orders-private...
    Creating file: inventory/stock_levels.csv in bucket: retail-orders-private...
    Creating file: exports/customer_pii.csv in bucket: retail-sensitive-public...
    Creating file: exports/payment_tokens.json in bucket: retail-sensitive-public...
    Creating file: findings/F-RET-001.json in bucket: retail-security-audit...
    Creating file: incidents/IR-2026-007.md in bucket: retail-security-audit...

    Success: Moto server populated with retail challenge data!
    ((chatbot.venv) ) jose@joses-MacBook-Pro the organization % 
    ```

---

## Chatbot Application Features

### Evaluation Set

An evaluation set of questions is included. It has 14 questions in three categories: `direct` (8 questions), `comparison` (3 questions), and `complex` (3 questions).

The ground-truth answer for each question is based on the `seed_data.py` script.

### Evaluation Metrics

Evaluation metrics include:

- `accuracy`: Percentage of questions answered correctly

- `average latency`: Measured in milliseconds. It is the time from sending a question to receiving the final model answer.

- `llm rounds`: Average number of model invocation rounds per question (`avg_llm_rounds`). It includes the first model response plus any extra model calls after tool execution.

- `relevance`: Judge score from 0 to 5 that measures how well the answer addresses the specific question and requested context.

- `coherence`: Judge score from 0 to 5 that measures logical flow, consistency, and clarity of the response.

- `conciseness`: Judge score from 0 to 5 that measures whether the answer is appropriately brief while still complete and useful.

### LLM-as-a-Judge

The evaluation runs in two steps: **first**, the chatbot generates an answer for each question; **second**, a judge LLM evaluates that answer against the ground truth. 

The judge returns a structured JSON verdict (`correct`, `partially_correct`, or `incorrect`) plus a short reason and quality scores for `relevance`, `coherence`, and `conciseness` on a 0 to 5 scale. 

This separation keeps answer generation and grading independent, making results easier to analyze and debug.

### Execution Tracing

A single `trace id` is assigned to each chatbot interaction session.

With this trace id, we track the session start and end, user input, model responses and tool calls, tool results, and tool-call rounds executed by the model.

The full trace sequence for one trace id is stored in PostgreSQL.

To access the sequence of traces for a specific trace id, you can use the `show_trace.py` script and the following command:

```bash
python scripts/show_trace.py --trace-id < trace_id >
```

```bash
((chatbot.venv) ) jose@joses-MacBook-Pro the organization % python scripts/show_trace.py --trace-id 441d991f-fdd8-4934-ad0b-9b6d1fa6d7d3
{
  "trace_id": "441d991f-fdd8-4934-ad0b-9b6d1fa6d7d3",
  "events_count": 12,
  "events": [
    {
      "trace_id": "441d991f-fdd8-4934-ad0b-9b6d1fa6d7d3",
      "event_index": 1,
      "event_type": "session_start",
      "payload": {
        "model": "gpt-5-mini",
        "trace_id": "441d991f-fdd8-4934-ad0b-9b6d1fa6d7d3",
        "question_id": "Q01",
        "temperature": 0.3,
        "question_type": "direct"
      },
      "created_at": "2026-02-18T08:10:33.122385+00:00"
    },
    {
      "trace_id": "441d991f-fdd8-4934-ad0b-9b6d1fa6d7d3",
      "event_index": 2,
      "event_type": "user_input",
      "payload": {
        "trace_id": "441d991f-fdd8-4934-ad0b-9b6d1fa6d7d3",
        "user_input": "What data does the S3 bucket retail-sensitive-public hold?"
      },
      "created_at": "2026-02-18T08:10:33.130048+00:00"
    },
    ...
```

### BOTO3-based AWS Tools

To let the chatbot interact with Moto, we defined 8 tools based on the boto3 Python SDK.


- `list_s3_buckets_tool`: Gets S3 bucket names.

-  `list_bucket_objects_tool`: Gets files inside an S3 bucket.

- `get_bucket_acl_tool`: Gets the grantees and permissions for an S3 bucket.

-  `get_bucket_metadata_configuration_tool`: Gets an S3 bucket metadata configuration.

- `get_bucket_policy_tool`: Gets the access policy for an S3 bucket.

- `get_bucket_policy_status_tool`: Gets the policy status (public or not public) for an S3 bucket.

- `describe_instances_tool`: Describes EC2 instance context with filters for specific instances.

- `describe_instance_types_tool`: Describes instance types available in the AWS account.


All these tools are bound to the LLM using the `ChatOpenAI` class.

No IAM management tools were added to the chatbot application. This was intentional so we can check whether the model hallucinates when asked about IAM user context.

### LLM Tool Execution Rounds

When a question is sent, the model generates an initial response; if that response includes tool calls, the application executes those tools and sends the tool results back to the model for another round. 

This loop continues until the model returns a final response with no additional tool calls or until the configured round limit is reached. 

The default maximum is `5` rounds (`MAX_TOOL_ROUNDS`), which prevents infinite tool-call loops while still allowing multi-step reasoning.


### Evaluation Results Output File

The file `evaluation/last_eval_results.json` is the final artifact produced by each batch evaluation run. It stores run-level metadata (chat model, judge model, total question count), aggregate metrics (`overall` and `by_type`), and detailed per-question records. 

Each question record includes the prompt, ground truth, chatbot answer, `trace_id`, latency, `llm_rounds`, unique tools executed, and the judge output (verdict, reason, and quality scores). 

This structure makes it easy to compare runs, investigate failures, and correlate low-scoring answers with trace events in PostgreSQL.

---

## Chatbot Application Execution Modes

### Interactive via terminal

You can start the chatbot application by running:

```bash
python main.py --model gpt-5-mini --temperature 0.2
```

```bash
((chatbot.venv) ) jose@joses-MacBook-Pro the organization % python main.py --model gpt-5-mini --temperature 0.2
the organization Chatbot (type 'exit' to quit) | trace_id=808f525c-c255-4e21-84ab-93c1947e64f0
Model: gpt-5-mini

You: What data does the S3 bucket retail-sensitive-public hold?
Assistant: The bucket retail-sensitive-public contains two objects: exports/customer_pii.csv and exports/payment_tokens.json.

Evidence: A bucket listing returned two keys — exports/customer_pii.csv (Size: 97 bytes, LastModified: 2026-02-18T07:16:55+00:00) and exports/payment_tokens.json (Size: 96 bytes, LastModified: 2026-02-18T07:16:55+00:00). I have not retrieved object contents, so I cannot confirm the exact fields or payloads inside those files; to verify data fields, fetch the objects (get-object) and inspect their contents.

You: 
```

### Batch evaluation

To run batch evaluation, use:

```bash
python evaluation/evaluate_chatbot.py --model gpt-5-mini --judge-model gpt-5-mini --temperature 0.3
```

```bash
((chatbot.venv) ) jose@joses-MacBook-Pro the organization % python evaluation/evaluate_chatbot.py --model gpt-5-mini --judge-model gpt-5-mini --temperature 0.3
[step1][Q01] type=direct latency_ms=28259.93 trace_id=441d991f-fdd8-4934-ad0b-9b6d1fa6d7d3
Q: What data does the S3 bucket retail-sensitive-public hold?
A: The bucket retail-sensitive-public contains two objects: exports/customer_pii.csv and exports/payment_tokens.json.

Evidence: list_bucket_objects returned KeyCount=2 with entries exports/customer_pii.csv (97 bytes, LastModified 2026-02-18T07:16:55Z) and exports/payment_tokens.json (96 bytes, LastModified 2026-02-18T07:16:55Z). I don’t have enough evidence to confirm the actual file contents (I did not download the objects); to verify the data you should retrieve the objects or view their object metadata.
--------------------------------------------------------------------------------
```

---

## Last Evaluation Results

| Scope | Chat Model | Judge Model | Questions | Accuracy % | Correct | Partial | Incorrect | Avg Latency (ms) | Avg LLM Rounds | Avg Relevance | Avg Coherence | Avg Conciseness |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Overall | gpt-5-mini | gpt-5-mini | 14 | 82.14 | 11 | 1 | 2 | 12053.51 | 2.21 | 4.50 | 4.86 | 4.79 |
| Direct | gpt-5-mini | gpt-5-mini | 8 | 75.00 | 6 | 0 | 2 | 10192.80 | 1.75 | 4.25 | 4.88 | 4.75 |
| Comparison | gpt-5-mini | gpt-5-mini | 3 | 100.00 | 3 | 0 | 0 | 13669.07 | 2.33 | 5.00 | 5.00 | 5.00 |
| Complex | gpt-5-mini | gpt-5-mini | 3 | 83.33 | 2 | 1 | 0 | 15399.82 | 3.33 | 4.67 | 4.67 | 4.67 |

Comparison questions performed best, with 100% accuracy and perfect quality scores. Direct questions were the weakest area, with the lowest accuracy (75%) and all incorrect answers. As question complexity increased, both LLM rounds and latency increased (from 1.75 rounds in direct to 3.33 rounds in complex). Overall answer quality remained high, with relevance, coherence, and conciseness all above 4.5.

---

## Challenges

### ACL and Access Policy Setup

Setting ACLs for AWS resources in Moto worked with the boto3 SDK, but policy behavior was harder to align in this mock setup.

Because ACL and policy status were not always aligned, some buckets could look public in one signal and not public in another signal.

Impact: this mismatch can confuse tool-based reasoning, reduce answer consistency for security questions, and lower evaluation scores even when tool calls are working as expected.

### Tool Calling Implementation via Langchain Ollama

At first, I planned to use an Ollama server and local models from HuggingFace and Ollama. After binding tools to `ChatOllama`, some models did not recognize the tools, so they could not answer tool-based questions.

I tested several models (Phi, Qwen, and Llama) with tool-calling support, from 1.5B to 8B parameters. Tool-calling behavior was not consistent across models in this setup.

I then created an OpenAI API key and switched the LangChain integration to `ChatOpenAI`.

### Traceability & Monitoring

There are several open-source tools for trace visualization and model-behavior analysis, but most of them require deploying multiple extra containers and services.

I decided to build a simple `traceability` module to collect telemetry across the chatbot execution lifecycle.

---

## Lessons Learned

- OpenAI models with tool-calling provided more consistent behavior for this challenge workflow.

- With a strong commercial model like GPT-5, we did not need to add too many `semantic hints` about tool relationships. However, this was tested with only 8 tools, so results may change with more tools and different question types.

- As expected, when question complexity increases, the number of tool execution rounds also increases. `Direct` = 1.8, `comparison` = 2.3, and `complex` = 3.3.

- The boto3 SDK includes functions that require different access levels. We used create/update functions only for data seeding, and read/query functions only as LLM tools. This separation helps route LLM requests in a safer way.

- Most unanswered questions happened because the chatbot still `needs additional tools`. This is a good sign, because the `chatbot does not invent answers` when it lacks the right tool.

---

## Next Steps

- Current chatbot performance evaluation is based on final results and efficient resource usage. A stronger evaluation process should also measure whether the tool-calling sequence is optimal.

- The current evaluation process does not include input/output token cost. We should add cost metrics to the final report.

- The current chatbot is designed for single-question inputs, not long conversations. Supporting longer conversations will likely require a stronger memory design to track question and answer history.

- Right now, average response time is about 12 seconds. If we need more complex workflows that chain multiple tools, we may need durable functions in the future.