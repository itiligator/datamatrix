# Руководство по запуску

## Запуск через Docker Compose

### Установка Docker и Docker Compose

1. Скачайте и установите Docker Desktop с [официального сайта Docker](https://www.docker.com/products/docker-desktop).
2. Убедитесь, что Docker Desktop запущен и работает.

### Настройка переменных окружения

1. Откройте файл `.env` в любом текстовом редакторе.
2. Убедитесь, что переменные окружения настроены правильно:
    ```dotenv
    URL=http://192.168.1.101:8080/photoaf.jpg
    TIMEOUT=2
    SHRINK=2
    EXPECTED_NUM=3
    FTP_HOST=localhost
    LOG_LEVEL=INFO
    HTTP_PORT=8081
    ```

### Запуск приложения с помощью Docker Compose

1. Откройте командную строку и перейдите в директорию вашего проекта:
    ```sh
    cd C:\path\to\your\project
    ```
2. Запустите Docker Compose:
    ```sh
    docker-compose up --build
    ```
Если выполнение команды прервалось с ошибкой, попробуйте снова.
### Просмотр результатов

1. Откройте веб-браузер и перейдите по адресу:
    ```
    http://localhost:8081
    ```
2. Вы увидите веб-интерфейс, где будет отображаться статус, состояние устройств, текущее состояние и список текущих задатекированных кодов.

Следуя этим шагам, вы сможете успешно запустить приложение и просматривать результаты его работы через веб-интерфейс, используя Docker Compose.