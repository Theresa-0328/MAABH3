import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Union

from pydantic import BaseModel
from rich import print

combat_path = Path(__file__).parent.parent.parent / "data" / "input.json"
output_path = Path(__file__).parent.parent.parent / "data" / "output.json"
json_template = {
    "recognition": "TemplateMatch",
    "template": "Combat/StopCombat.png",
    "roi": [0, 0, 136, 140],
    "action": "Custom",
    "pre_delay": 0,
    "post_delay": 0,
    "next": [],
}
default_pre_delay = 50
default_post_delay = 50
action_list = [
    {"action": "Forward", "pre_delay": 0, "post_delay": 50},
    {"action": "Backward", "pre_delay": 0, "post_delay": 50},
    {"action": "Left", "pre_delay": 0, "post_delay": 50},
    {"action": "Right", "pre_delay": 0, "post_delay": 50},
    {"action": "Left Forward", "pre_delay": 0, "post_delay": 50},
    {"action": "Left Backward", "pre_delay": 0, "post_delay": 50},
    {"action": "Right Forward", "pre_delay": 0, "post_delay": 50},
    {"action": "Right Backward", "pre_delay": 0, "post_delay": 50},
    {"action": "BasicATK", "pre_delay": 0, "post_delay": 200},
    {"action": "BasicATKCharge", "pre_delay": 0, "post_delay": 100},
    {"action": "Evade", "pre_delay": 0, "post_delay": 150},
    {"action": "Ultimate", "pre_delay": 0, "post_delay": 150},
    {"action": "UltimateCharge", "pre_delay": 0, "post_delay": 100},
    {"action": "WeaponSkill", "pre_delay": 0, "post_delay": 150},
    {"action": "ELFSkill", "pre_delay": 0, "post_delay": 150},
    {"action": "ExtraSkill", "pre_delay": 0, "post_delay": 100},
]


class Action(BaseModel):
    pre_delay: int
    post_delay: int


class Combat(BaseModel):
    mode: str
    role: str
    version: str
    combat: List[Union[str, Dict[str, List[int]]]]


def default_delay(data: str) -> Action:
    """根据动作名称，返回对应的预延迟和后延迟。

    参数:
        data (str): 动作名称

    返回:
        Action: 包含预延迟和后延迟的对象
    """
    # movement = action_list[:8]
    # qte = action_list[8:10]  # noqa: F841
    # skills = action_list[10:]  # noqa: F841

    for action_dict in action_list:
        if action_dict["action"] == data:
            return Action(
                pre_delay=action_dict["pre_delay"], post_delay=action_dict["post_delay"]
            )

    # 如果没有找到匹配的动作，返回默认值
    return Action(pre_delay=default_pre_delay, post_delay=default_post_delay)


def generate_from_combat(combat: List, mode: str, role: str) -> Dict:
    """
    根据 combat 列表生成 JSON 对象。

    参数:
        combat (List): 包含 "combat" 操作的列表。
        mode (str): 模式名称。
        role (str): 角色名称。

    返回:
        dict: 生成的 JSON 对象。
    """
    global json_template
    generated_json = {}
    next_index = 0

    for idx, item in enumerate(combat):
        data = json_template.copy()
        if isinstance(item, str):
            data["custom_action"] = item
            delay = default_delay(item)
            data["pre_delay"] = delay.pre_delay
            data["post_delay"] = delay.post_delay

        elif isinstance(item, dict):
            for key, value in item.items():
                data["custom_action"] = key
                if isinstance(value, list) and len(value) == 2:
                    data["pre_delay"] = value[0]
                    data["post_delay"] = value[1]
                else:
                    delay = default_delay(key)
                    data["pre_delay"] = delay.pre_delay
                    data["post_delay"] = delay.post_delay

        next_step = f"{mode}Combat{role}_{str(next_index + 1).zfill(3)}"
        data["next"] = [f"{mode}Combat{role}Finish", next_step]

        if idx == 0:
            current_step = f"{mode}Combat{role}Preheat"
            data["pre_delay"] = 1000
            data["post_delay"] = 1000
        else:
            current_step = f"{mode}Combat{role}_{str(next_index).zfill(3)}"

        generated_json[current_step] = data

        # 更新 next_index
        next_index += 1

    try:
        if generated_json:
            last_step = f"{mode}Combat{role}_{str(next_index - 1).zfill(3)}"
            generated_json[last_step]["next"] = [f"{mode}CombatFinish"]
    except KeyError:
        print("[bold red]生成 JSON 失败！[/bold red]")
        print("[bold red]请检查输入的 JSON 是否符合要求。[/bold red]")

    return generated_json


def reverse_to_combat(json_data: Dict) -> Combat:
    """
    将 JSON 对象解析为 Combat 对象。

    参数:
        json_data (Dict): 输入的 JSON 对象。

    返回:
        Combat: 解析后的 Combat 对象。
    """
    combat_list = []
    mode = None
    role = None

    sorted_keys = sorted(json_data.keys())

    for key in sorted_keys:
        action_data = json_data[key]
        custom_action = action_data["custom_action"]
        pre_delay = action_data["pre_delay"]
        post_delay = action_data["post_delay"]

        # 解析 mode 和 role
        if mode is None and role is None:
            match = re.search(r"(.+)Combat(.+)Preheat", key)
            if match:
                mode, role = match.groups()

        # 获取该动作的默认延迟值
        default_action = default_delay(custom_action)

        # 构建 combat_list
        if (
            pre_delay == default_action.pre_delay
            and post_delay == default_action.post_delay
        ):
            combat_list.append(custom_action)
        elif pre_delay == 1000 and post_delay == 1000:
            combat_list.append(custom_action)
        else:
            combat_list.append({custom_action: [pre_delay, post_delay]})

    return Combat(mode=mode, role=role, version="debug", combat=combat_list)


def read_file(path: Path) -> Dict:
    """读取指定路径的文件内容。

    参数:
        path (Path): 文件路径。

    返回:
        Optional[str]: 文件内容，如果发生异常则返回 None。

    异常:
        如果文件不存在、无权限或其他I/O错误，函数将返回 None。
    """
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, PermissionError, IOError) as e:
        print(f"读取文件失败：{e}")
        raise e


def save_file(path: Path, content) -> bool:
    """将内容保存到指定路径的文件中。

    参数:
        path (Path): 文件路径。
        content: 要保存的内容。

    返回:
        bool: 如果保存成功返回 True，否则返回 False。

    异常:
        如果没有写权限或其他I/O错误，函数将返回 False。
    """
    try:
        with open(path, "w") as f:
            json.dump(content, f)
            print(f"保存文件成功：{path}")
        return True
    except (PermissionError, IOError) as e:
        print(f"保存文件失败：{e}")
        raise e


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="反序列化生成的Combat文件")
    parser.add_argument("-p", "--param", action="store_true", help="反序列器")
    args = parser.parse_args()
    if args.param:
        output_model = reverse_to_combat(read_file(combat_path))
        print(f"角色名{output_model.role}, 版本号{output_model.version}")
        save_file(output_path, output_model.model_dump())
    else:
        file = read_file(combat_path)
        input_model = Combat.model_validate(file)
        print(f"角色名{input_model.role}, 版本号{input_model.version}")
        save_file(
            output_path,
            generate_from_combat(
                input_model.combat, input_model.mode, input_model.role
            ),
        )
