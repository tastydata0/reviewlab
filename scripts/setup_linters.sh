#!/bin/bash

# Создаем структуру директорий
mkdir -p bin/linters/configs

# Версия Checkstyle
CHECKSTYLE_VERSION="10.12.4"

# Пути к конфигам Checkstyle (КРИТИЧНО: скачиваем из тега конкретной версии, а не из master!)
echo "Downloading Checkstyle configs for version ${CHECKSTYLE_VERSION}..."
curl -s -o bin/linters/configs/google_checks.xml "https://raw.githubusercontent.com/checkstyle/checkstyle/checkstyle-${CHECKSTYLE_VERSION}/src/main/resources/google_checks.xml"
curl -s -o bin/linters/configs/sun_checks.xml "https://raw.githubusercontent.com/checkstyle/checkstyle/checkstyle-${CHECKSTYLE_VERSION}/src/main/resources/sun_checks.xml"

# Скачиваем Checkstyle JAR
echo "Downloading Checkstyle JAR version ${CHECKSTYLE_VERSION}..."
curl -s -L -o bin/linters/checkstyle-all.jar "https://github.com/checkstyle/checkstyle/releases/download/checkstyle-${CHECKSTYLE_VERSION}/checkstyle-${CHECKSTYLE_VERSION}-all.jar"

# Создаем wrapper-скрипт для checkstyle
cat > bin/linters/checkstyle <<'EOF'
#!/bin/bash
# Находим директорию, где лежит сам скрипт
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
java -jar "$SCRIPT_DIR/checkstyle-all.jar" "$@"
EOF
chmod +x bin/linters/checkstyle


echo "--------------------------------------------------"
echo "Линтеры подготовлены!"
echo "1. Python: 'flake8' установлен через pip (uv)."
echo "2. C++: 'cppcheck' должен быть установлен в системе."
echo "3. Java: 'checkstyle' и конфиги ${CHECKSTYLE_VERSION} скачаны в bin/linters/."
echo "--------------------------------------------------"
