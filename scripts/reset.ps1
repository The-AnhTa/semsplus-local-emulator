param([string]$BaseUrl = "http://localhost:8080")

$response = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/admin/reset" -ContentType "application/json"
$response | ConvertTo-Json -Depth 5

