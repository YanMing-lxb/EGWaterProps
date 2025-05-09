'''
 =======================================================================
 ····Y88b···d88P················888b·····d888·d8b·······················
 ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 ······Y88o88P··················88888b·d88888···························
 ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 ·······························································888·····
 ··························································Y8b·d88P·····
 ···························································"Y88P"······
 =======================================================================

 -----------------------------------------------------------------------
Author       : 焱铭
Date         : 2025-04-22 15:58:52 +0800
LastEditTime : 2025-04-22 16:16:18 +0800
Github       : https://github.com/YanMing-lxb/
FilePath     : /egasp/tools/make.py
Description  : 
 -----------------------------------------------------------------------
'''

import subprocess
import shutil
import re
import sys
from pathlib import Path
from rich.console import Console

console = Console()


def _remove_paths(paths):
    for path in paths:
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink()
            console.log(f"已删除: {path}")

def _run_command(command, check=True):
    try:
        subprocess.run(command, check=check)
    except subprocess.CalledProcessError as e:
        console.log(f"执行命令时出错: {e}")
        sys.exit(1)

def clean():
    dirs_to_remove = ['build', 'dist', Path('src') / 'egasp.egg-info']
    pycache_dirs = Path('.').rglob('__pycache__')
    pyc_files = Path('.').rglob('*.pyc')

    _remove_paths([Path(d) for d in dirs_to_remove])
    _remove_paths(pycache_dirs)
    _remove_paths(pyc_files)

    console.log("清理完成")


def build_all():
    _run_command(['python', '-m', 'build'])
    console.log("构建完成")


def html():
    readme_md = Path('README.md')
    readme_html = Path('README.html')
    target_dir = Path('src/egasp/data')
    
    _run_command(['pandoc', str(readme_md), '-o', str(readme_html)])
    
    if not target_dir.exists():
        target_dir.mkdir(parents=True)
        console.log(f"已创建目录: {target_dir}")
    
    target_html = target_dir / 'README.html'
    shutil.move(str(readme_html), str(target_html))
    console.log(f"生成 HTML 并移动到 {target_html}")


def rst():
    readme_md = Path('README.md')
    readme_rst = Path('README.rst')
    _run_command(['pandoc', '-s', '-t', 'rst', str(readme_md), '-o', str(readme_rst)])
    console.log("生成 RST 文件")

def run_tests():
    _run_command(['python', 'tests/test.py'])
    console.log("测试完成")

def testwhl():
    clean()
    build_all()
    _run_command(['pip', 'uninstall', '-y', 'egasp'])
    whl_files = list(Path('dist').glob('*.whl'))
    if not whl_files:
        raise FileNotFoundError("dist 目录中没有找到 .whl 文件")
    _run_command(['pip', 'install', str(whl_files[0])])
    _run_command(['python', 'tests/test.py', '-w'])
    _run_command(['pip', 'uninstall', '-y', 'egasp'])
    clean()
    console.log("测试 .whl 文件完成")


def inswhl():
    clean()
    build_all()
    _run_command(['pip', 'uninstall', '-y', 'egasp'])
    whl_files = list(Path('dist').glob('*.whl'))
    if not whl_files:
        raise FileNotFoundError("dist 目录中没有找到 .whl 文件")
    _run_command(['pip', 'install', str(whl_files[0])])
    console.log("安装 egasp*.whl 成功")


def _get_version():
    version_file = Path('src/egasp/version.py')
    if not version_file.exists():
        raise FileNotFoundError(f"文件 {version_file} 不存在")
    
    with open(version_file, 'r', encoding='utf-8') as file:
        content = file.read()
    
    version_match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", content)
    if not version_match:
        raise ValueError(f"无法在 {version_file} 中找到 __version__ 变量")
    
    return version_match.group(1)


def upload():
    version = _get_version()
    tag_name = f"v{version}"
    
    # 创建标签
    _run_command(['git', 'tag', tag_name])
    console.log(f"创建标签: {tag_name}")
    
    # 推送标签
    _run_command(['git', 'push', 'origin', tag_name])
    console.log(f"推送标签: {tag_name}")
    
    clean()
    console.log("成功上传标签和推送到远程仓库，发布到 github")


def _contains_uncommented_set_language(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.readlines()
    
    for line in content:
        # 去除行首和行尾的空白字符
        stripped_line = line.strip()
        # 检查是否包含未注释的 _ = set_language('config')
        if re.match(r"^\s*_\s*=\s*set_language\(.+\)\s*$", stripped_line):
            return True
    return False

def _get_modules():
    modules = []
    for f in Path('src/egasp').glob('*.py'):
        if _contains_uncommented_set_language(f):
            modules.append(f.stem)
    return modules

def _generate_pot_files(locale_dir, modules):
    for module in modules:
        py_file = Path(f'src/egasp/{module}.py')
        temp_pot = locale_dir / f'{module}-temp.pot'
        _run_command(['xgettext', '--output', str(temp_pot), str(py_file)])
        console.log(f"生成临时 .pot 文件: {temp_pot}")


def _update_pot_files(locale_dir, modules):
    for module in modules:
        temp_pot = locale_dir / f'{module}-temp.pot'
        original_pot = locale_dir / f'{module}.pot'
        
        if not original_pot.exists():
            if temp_pot.exists():
                temp_pot.rename(original_pot)
                console.log(f"原始 .pot 文件 {original_pot} 不存在：\n将临时 .pot 文件 {temp_pot} 重命名为 {original_pot}")
            else:
                console.log(f"警告: 临时 .pot 文件 {temp_pot} 不存在，跳过更新")
            continue
        
        _run_command(['msgmerge', '--update', str(original_pot), str(temp_pot)])
        console.log(f"更新 .pot 文件: {original_pot}")

def _generate_mo_files(locale_dir, modules):
    for module in modules:
        pot_file = locale_dir / f'{module}.pot'
        mo_dir = locale_dir / 'LC_MESSAGES'
        mo_dir.mkdir(exist_ok=True, parents=True)
        mo_file = mo_dir / f'{module}.mo'

        if not pot_file.exists():
            console.log(f"警告: {pot_file} 不存在，跳过更新")
            continue

        _run_command(['msgfmt', '-o', str(mo_file), str(pot_file)])
        console.log(f"生成 .mo 文件: {mo_file}")

def _cleanup_temp_pot_files(locale_dir, modules):
    for module in modules:
        temp_pot = locale_dir / f'{module}-temp.pot'
        if temp_pot.exists():
            temp_pot.unlink()
            console.log(f"删除临时 .pot 文件: {temp_pot}")

def pot():
    locale_dir = Path('src/egasp/locale/en')
    modules = _get_modules()
    _generate_pot_files(locale_dir, modules)
    console.log("生成 .pot 文件完成")


def mo():
    locale_dir = Path('src/egasp/locale/en')
    modules = _get_modules()
    _generate_mo_files(locale_dir, modules)
    console.log("生成 .mo 文件完成")


def poup():
    locale_dir = Path('src/egasp/locale/en')
    modules = _get_modules()
    _generate_pot_files(locale_dir, modules)
    _update_pot_files(locale_dir, modules)
    _generate_mo_files(locale_dir, modules)
    _cleanup_temp_pot_files(locale_dir, modules)
    console.log("更新 .pot 和 .mo 文件完成")

def main():
    targets = {
        'all': build_all,
        'clean': clean,
        'html': html,
        'rst': rst,
        'test': run_tests,
        'testwhl': testwhl,
        'inswhl': inswhl,
        'upload': upload,
        'pot': pot,
        'mo': mo,
        'poup': poup,
    }

    if len(sys.argv) < 2 or sys.argv[1] not in targets:
        console.log(f"用法: {sys.argv[0]} <目标>")
        console.log("可用目标:", ', '.join(targets.keys()))
        sys.exit(1)

    target = sys.argv[1]
    try:
        targets[target]()
    except subprocess.CalledProcessError as e:
        console.log(f"执行命令时出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
