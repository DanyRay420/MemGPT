import json
import re

from colorama import Fore, Style, init

from memgpt.utils import printd

init(autoreset=True)

# DEBUG = True  # puts full message outputs in the terminal
DEBUG = False  # only dumps important messages in the terminal

STRIP_UI = False


def important_message(msg):
    fstr = f"{Fore.MAGENTA}{Style.BRIGHT}{{msg}}{Style.RESET_ALL}"
    if STRIP_UI:
        fstr = "{msg}"
    print(fstr.format(msg=msg))


def warning_message(msg):
    fstr = f"{Fore.RED}{Style.BRIGHT}{{msg}}{Style.RESET_ALL}"
    if STRIP_UI:
        fstr = "{msg}"
    else:
        print(fstr.format(msg=msg))


async def internal_monologue(msg):
    # ANSI escape code for italic is '\x1B[3m'
    fstr = f"\x1B[3m{Fore.LIGHTBLACK_EX}💭 {{msg}}{Style.RESET_ALL}"
    if STRIP_UI:
        fstr = "{msg}"
    print(fstr.format(msg=msg))


async def assistant_message(msg):
    fstr = f"{Fore.YELLOW}{Style.BRIGHT}🤖 {Fore.YELLOW}{{msg}}{Style.RESET_ALL}"
    if STRIP_UI:
        fstr = "{msg}"
    print(fstr.format(msg=msg))


async def memory_message(msg):
    fstr = f"{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}🧠 {Fore.LIGHTMAGENTA_EX}{{msg}}{Style.RESET_ALL}"
    if STRIP_UI:
        fstr = "{msg}"
    print(fstr.format(msg=msg))


async def system_message(msg):
    fstr = f"{Fore.MAGENTA}{Style.BRIGHT}🖥️ [system] {Fore.MAGENTA}{msg}{Style.RESET_ALL}"
    if STRIP_UI:
        fstr = "{msg}"
    print(fstr.format(msg=msg))


async def user_message(msg, raw=False, debug=DEBUG):
    def print_user_message(icon, msg, printf=print):
        if STRIP_UI:
            printf(f"{icon} {msg}")
        else:
            printf(f"{Fore.GREEN}{Style.BRIGHT}{icon} {Fore.GREEN}{msg}{Style.RESET_ALL}")

    def printd_user_message(icon, msg):
        return print_user_message(icon, msg)

    if isinstance(msg, str):
        if raw:
            printd_user_message("🧑", msg)
            return
        else:
            try:
                msg_json = json.loads(msg)
            except:
                printd(f"Warning: failed to parse user message into json")
                printd_user_message("🧑", msg)
                return
    if msg_json["type"] == "user_message":
        msg_json.pop("type")
        printd_user_message("🧑", msg_json)
    elif msg_json["type"] == "heartbeat":
        if debug:
            msg_json.pop("type")
            printd_user_message("💓", msg_json)
    elif msg_json["type"] == "system_message":
        msg_json.pop("type")
        printd_user_message("🖥️", msg_json)
    else:
        printd_user_message("🧑", msg_json)


async def function_message(msg, debug=DEBUG):
    def print_function_message(icon, msg, color=Fore.RED, printf=print):
        if STRIP_UI:
            printf(f"⚡{icon} [function] {msg}")
        else:
            printf(f"{color}{Style.BRIGHT}⚡{icon} [function] {color}{msg}{Style.RESET_ALL}")

    def printd_function_message(icon, msg, color=Fore.RED):
        return print_function_message(icon, msg, color, printf=(print if debug else printd))

    if isinstance(msg, dict):
        printd_function_message("", msg)
        return

    if msg.startswith("Success: "):
        printd_function_message("🟢", msg)
    elif msg.startswith("Error: "):
        printd_function_message("🔴", msg)
    elif msg.startswith("Running "):
        if debug:
            printd_function_message("", msg)
        else:
            if "memory" in msg:
                match = re.search(r"Running (\w+)\((.*)\)", msg)
                if match:
                    function_name = match.group(1)
                    function_args = match.group(2)
                    print_function_message("🧠", f"updating memory with {function_name}")
                    try:
                        msg_dict = eval(function_args)
                        if function_name == "archival_memory_search":
                            output = f'\tquery: {msg_dict["query"]}, page: {msg_dict["page"]}'
                            if STRIP_UI:
                                print(output)
                            else:
                                print(f"{Fore.RED}{output}")
                        else:
                            if STRIP_UI:
                                print(f'\t {msg_dict["old_content"]}\n\t→ {msg_dict["new_content"]}')
                            else:
                                print(f'{Style.BRIGHT}\t{Fore.RED} {msg_dict["old_content"]}\n\t{Fore.GREEN}→ {msg_dict["new_content"]}')
                    except Exception as e:
                        printd(e)
                        printd(msg_dict)
                        pass
                else:
                    printd(f"Warning: did not recognize function message")
                    printd_function_message("", msg)
            elif "send_message" in msg:
                # ignore in debug mode
                pass
            else:
                printd_function_message("", msg)
    else:
        try:
            msg_dict = json.loads(msg)
            if "status" in msg_dict and msg_dict["status"] == "OK":
                printd_function_message("", str(msg), color=Fore.GREEN)
            else:
                printd_function_message("", str(msg), color=Fore.RED)
        except Exception:
            print(f"Warning: did not recognize function message {type(msg)} {msg}")
            printd_function_message("", msg)


async def print_messages(message_sequence, dump=False):
    idx = len(message_sequence)
    for msg in message_sequence:
        if dump:
            print(f"[{idx}] ", end="")
            idx -= 1
        role = msg["role"]
        content = msg["content"]

        if role == "system":
            await system_message(content)
        elif role == "assistant":
            # Differentiate between internal monologue, function calls, and messages
            if msg.get("function_call"):
                if content is not None:
                    await internal_monologue(content)
                # I think the next one is not up to date
                # await function_message(msg["function_call"])
                args = json.loads(msg["function_call"].get("arguments"))
                await assistant_message(args.get("message"))
                # assistant_message(content)
            else:
                await internal_monologue(content)
        elif role == "user":
            await user_message(content, debug=dump)
        elif role == "function":
            await function_message(content, debug=dump)
        else:
            print(f"Unknown role: {content}")


async def print_messages_simple(message_sequence):
    for msg in message_sequence:
        role = msg["role"]
        content = msg["content"]

        if role == "system":
            await system_message(content)
        elif role == "assistant":
            await assistant_message(content)
        elif role == "user":
            await user_message(content, raw=True)
        else:
            print(f"Unknown role: {content}")


async def print_messages_raw(message_sequence):
    for msg in message_sequence:
        print(msg)
