# Путь к папке, за которой следим
$watchFolder = "C:\Users\Andrei\PycharmProjects\datamatrix\results\labels"

# Создаем объект наблюдателя
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $watchFolder
$watcher.Filter = "*.pdf"  # Следим только за PDF-файлами
$watcher.EnableRaisingEvents = $true
$watcher.IncludeSubdirectories = $false

# Хэш-таблица для отслеживания обработанных файлов
$processedFiles = @{}

# Действие при появлении нового файла
$action = {
    Start-Sleep -Seconds 2  # Даем файлу "дозаписаться", если он большой
    $filePath = $Event.SourceEventArgs.FullPath

    # Проверяем, был ли файл уже обработан
    if (-not $processedFiles.ContainsKey($filePath)) {
        $processedFiles[$filePath] = $true  # Помечаем файл как обработанный
        Write-Host "Найден новый файл: $filePath"

        # Проверяем, что файл не изменялся в течение 2 секунд
        Start-Sleep -Seconds 2
        $initialWriteTime = (Get-Item $filePath).LastWriteTime
        Start-Sleep -Seconds 2
        $currentWriteTime = (Get-Item $filePath).LastWriteTime

        if ($initialWriteTime -eq $currentWriteTime) {
            try {
                # Печать файла
                Start-Process -FilePath $filePath -Verb Print -PassThru | Out-Null
                Write-Host "Файл отправлен на печать: $filePath"
            } catch {
                Write-Host "Ошибка при печати: $_"
            }
        } else {
            Write-Host "Файл всё ещё изменяется: $filePath"
        }
    } else {
        Write-Host "Файл уже обработан: $filePath"
    }
}

# Регистрируем событие
Register-ObjectEvent $watcher "Created" -Action $action

# Чтобы скрипт оставался активным
Write-Host "Ожидание новых файлов для печати... (нажмите Ctrl+C для выхода)"
while ($true) {
    Start-Sleep -Seconds 5
}