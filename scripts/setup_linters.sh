#!/bin/bash

# Создаем структуру директорий
mkdir -p bin/linters/configs

# Версия Checkstyle
CHECKSTYLE_VERSION="10.12.4"

# Пути к конфигам Checkstyle
echo "Downloading Checkstyle configs for version ${CHECKSTYLE_VERSION}..."
curl -s -o bin/linters/configs/google_checks.xml "https://raw.githubusercontent.com/checkstyle/checkstyle/checkstyle-${CHECKSTYLE_VERSION}/src/main/resources/google_checks.xml"
curl -s -o bin/linters/configs/sun_checks.xml "https://raw.githubusercontent.com/checkstyle/checkstyle/checkstyle-${CHECKSTYLE_VERSION}/src/main/resources/sun_checks.xml"

# Создаем "расслабленный" конфиг для студентов на базе Google Style
# 1. Удаляем проверку Indentation (она слишком строгая и требует 2 пробела)
# 2. Удаляем проверку OuterTypeFilename (чтобы не ругалось на несовпадение имени файла и класса)
# 3. Удаляем проверку JavadocMethod (студенты редко пишут доки)
echo "Creating relaxed ReviewLab config..."
cp bin/linters/configs/google_checks.xml bin/linters/configs/reviewlab_checks.xml

# Используем python для надежного удаления XML узлов
python3 - <<EOF
import sys
import os

filepath = 'bin/linters/configs/reviewlab_checks.xml'
with open(filepath, 'r') as f:
    lines = f.readlines()

modules_to_remove = ['Indentation', 'OuterTypeFilename', 'JavadocMethod', 'MissingJavadocMethod']
output = []
skip = False
for line in lines:
    if any(f'name="{m}"' in line for m in modules_to_remove):
        if '/>' not in line: # It's a block
            skip = True
        continue
    if skip and '</module>' in line:
        skip = False
        continue
    if not skip:
        output.append(line)

with open(filepath, 'w') as f:
    f.writelines(output)
EOF

# Скачиваем Checkstyle JAR
echo "Downloading Checkstyle JAR version ${CHECKSTYLE_VERSION}..."
curl -s -L -o bin/linters/checkstyle-all.jar "https://github.com/checkstyle/checkstyle/releases/download/checkstyle-${CHECKSTYLE_VERSION}/checkstyle-${CHECKSTYLE_VERSION}-all.jar"

# Создаем wrapper-скрипт для checkstyle
cat > bin/linters/checkstyle <<'EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
java -jar "$SCRIPT_DIR/checkstyle-all.jar" "$@"
EOF
chmod +x bin/linters/checkstyle

echo "--------------------------------------------------"
echo "Линтеры подготовлены!"
echo "1. Python: 'flake8' установлен."
echo "2. C++: 'cppcheck' должен быть в системе."
echo "3. Java: 'checkstyle' и конфиги скачаны."
echo "   Используется кастомный 'reviewlab_checks.xml' (без Indentation)."
echo "--------------------------------------------------"
