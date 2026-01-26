Add-Type -AssemblyName System.Drawing

$sourcePath = "D:\ai_editing\workspace\LocalClip-Editor\logo.jpg"
$destPath = "D:\ai_editing\workspace\LocalClip-Editor\logo.ico"

# Load the image
$img = [System.Drawing.Image]::FromFile($sourcePath)

# Create a 256x256 bitmap for the icon
$size = 256
$bitmap = New-Object System.Drawing.Bitmap($size, $size)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$graphics.DrawImage($img, 0, 0, $size, $size)
$graphics.Dispose()

# Convert to icon and save
$icon = [System.Drawing.Icon]::FromHandle($bitmap.GetHicon())
$fs = [System.IO.FileStream]::new($destPath, [System.IO.FileMode]::Create)
$icon.Save($fs)
$fs.Close()

# Cleanup
$bitmap.Dispose()
$img.Dispose()

Write-Host "Icon created at: $destPath"
