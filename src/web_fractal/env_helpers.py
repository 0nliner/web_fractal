import os
import typing as t


def get_bool_from_env(env_var_name: str) -> bool:
    env_value = os.environ.get(env_var_name)
    if env_value is None:
        return False
    if env_value.lower() == "true" or env_value.lower() == "1":
        return True

    return False


def get_list_from_env(env_var_name: str) -> list[str]:
    env_value = os.environ.get(env_var_name)

    if env_value is not None and env_value != "":
        return env_value.split(",")
    else:
        return []


def get_int_from_env(env_var_name: str, default: t.Optional[int] = None) -> int:
    env_value = os.environ.get(env_var_name)
    if env_value and isinstance(default, int):
        return default

    return int(env_value)


def get_env_content() -> dict[str, t.Any]:
    env_content = {key: val for key, val in os.environ.items()}
    return env_content