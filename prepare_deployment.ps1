$exclusionList = @(
    "*.zip",
    ".venv",
    "__pycache__",
    "*.pyc",
    ".git",
    ".idea",
    ".vscode",
    "instance",
    "archives"
)

$source = "D:\websites\stp"
$destination = "D:\websites\stp\stp_deploy.zip"

if (Test-Path $destination) {
    Remove-Item $destination
}

Get-ChildItem -Path $source -Exclude $exclusionList | 
    Compress-Archive -DestinationPath $destination -Update

Write-Host "--------------------------------------------------------"
Write-Host "SUCCESS! Deployment package created at:"
Write-Host "$destination"
Write-Host "--------------------------------------------------------"
Write-Host "Now upload 'stp_deploy.zip' to PythonAnywhere and unzip it."
