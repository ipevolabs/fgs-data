import json
import numpy as np
import sys
import argparse
import datetime
from collections import defaultdict
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
def validate_dataset(dataset):
    # Format error checks
    format_errors = defaultdict(int)
    for ex in dataset:
        if not isinstance(ex, dict):
            format_errors["data_type"] += 1
            continue
        messages = ex.get("messages", None)
        if not messages:
            format_errors["missing_messages_list"] += 1
            continue
        for message in messages:
            if "role" not in message or "content" not in message:
                format_errors["message_missing_key"] += 1
            if any(k not in ("role", "content", "name", "function_call", "weight") for k in message):
                format_errors["message_unrecognized_key"] += 1
            if message.get("role", None) not in ("system", "user", "assistant", "function"):
                format_errors["unrecognized_role"] += 1
            content = message.get("content", None)
            function_call = message.get("function_call", None)
            if (not content and not function_call) or not isinstance(content, str):
                format_errors["missing_content"] += 1
        if not any(message.get("role", None) == "assistant" for message in messages):
            format_errors["example_missing_assistant_message"] += 1
    if format_errors:
        print("Found errors:")
        for k, v in format_errors.items():
            print(f"{k}: {v}")
        return False
    return True


sysprompt = "你是一個佛學專家, 精通中英文佛教詞彙, 將user輸入的中文翻譯為英文."
def fgsentry_to_oaift( fgse):
    #print('.translation keys=', fgse['translation'].keys())
    sentence = fgse['translation']['sentences'][0]
    return {
        "messages": [
            {"role": "system", "content": sysprompt},
            {"role": "user", "content": sentence['zh']},
            {"role": "assistant", "content": sentence['en']}
        ]
    }

def load_dataset( infn):
    dataset=[]
    with open( infn, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                fgse = json.loads(line)
                if not 'sentences' in fgse['translation']:
                    continue
                oaifte = fgsentry_to_oaift( fgse)
                dataset.append(oaifte)
            except Exception as e:
                print('faile to convert entry line:',  line)
        return dataset

def save_dataset( dataset, jsonlfn):
    with open( jsonlfn, 'w', encoding='utf-8') as file:
        for d in dataset:
            file.write(json.dumps( d, ensure_ascii=False) + '\n')

def oaift_start( jslfn, model):
    client = OpenAI()
    fobj = client.files.create(
        file=open(  jslfn, "rb"),
        purpose="fine-tune"
    )
    job = client.fine_tuning.jobs.create(
        training_file=fobj.id,
        model=model
    )
    print(job)

def oaift_jobs():
    client = OpenAI()
    # List 10 fine-tuning jobs
    jobs = client.fine_tuning.jobs.list(limit=10)
    print(jobs)
    # Retrieve the state of a fine-tune
    #client.fine_tuning.jobs.retrieve("ftjob-abc123")
    # Cancel a job
    #client.fine_tuning.jobs.cancel("ftjob-abc123")
    # List up to 10 events from a fine-tuning job
    #client.fine_tuning.jobs.list_events(fine_tuning_job_id="ftjob-abc123", limit=10)
    #Delete a fine-tuned model (must be an owner of the org the model was created in)
    #client.models.delete("ft:gpt-3.5-turbo:acemeco:suffix:abc123")

def oaift_clean( jobid):
    client = OpenAI()
    #Cancel a job
    client.fine_tuning.jobs.cancel( jobid)

def generate_ftname():
    now = datetime.datetime.now()
    date_time_str = now.strftime('%Y%m%d%H%M%S%f')[:18]
    return f"file-fgs-tl-{date_time_str}"

def main_finetune( infn, model):
    dataset = load_dataset(infn)
    if not validate_dataset(dataset):
        return
    jslfn='tmp.jsonl'
    save_dataset( dataset, jslfn)
    oaift_start(jslfn, model)

def main():
    parser = argparse.ArgumentParser(description="Finetune OpenAI model the FGS dataset")
    subparsers = parser.add_subparsers(dest='command', help='available commands')
    # 'start' command
    start_parser = subparsers.add_parser('start', help='Start the process')
    start_parser.add_argument('datafile', type=str, help='Path to the FGS dataset file in JSONL format.')
    start_parser.add_argument('--model', type=str, default='gpt-4o-mini-2024-07-18', help='The OpenAI base model to finetune.  Default: gpt-4o-mini')
    clean_parser = subparsers.add_parser('clean', help='Clean the finetune jobs')
    list_parser = subparsers.add_parser('list', help='List the finetune jobs')
    args = parser.parse_args()
    if args.command == 'start':
        main_finetune( args.datafile, args.model)
    elif args.command == 'clean':
        oaift_clean()
    elif args.command == 'list':
        oaift_jobs()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
