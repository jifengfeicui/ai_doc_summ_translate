# 应用图标目录

此目录用于存放 Electron 应用的图标文件。

## 需要的图标文件

- **Windows**: `icon.ico` (推荐 256x256 像素)
- **macOS**: `icon.icns` (推荐 512x512 像素)
- **Linux**: `icon.png` (推荐 512x512 像素)

## 图标规格说明

### Windows (.ico)
- 推荐包含多种尺寸: 16x16, 32x32, 48x48, 64x64, 128x128, 256x256
- 格式: ICO
- 文件名: `icon.ico`

### macOS (.icns)
- 推荐包含多种尺寸: 16x16, 32x32, 64x64, 128x128, 256x256, 512x512, 1024x1024
- 格式: ICNS
- 文件名: `icon.icns`

### Linux (.png)
- 推荐尺寸: 512x512
- 格式: PNG (透明背景)
- 文件名: `icon.png`

## 如何生成图标

### 方法一: 在线工具 (推荐)

使用以下在线工具转换图标:

- [icoconvert.com](https://icoconvert.com/) - 支持多种格式转换
- [cloudconvert.com](https://cloudconvert.com/) - 强大的在线转换工具
- [convertico.com](https://convertico.com/) - 专门的 ICO 转换工具

**步骤:**
1. 准备一张 1024x1024 的 PNG 图片 (透明背景最佳)
2. 上传到在线工具
3. 选择目标格式 (ico, icns, png)
4. 下载并重命名为对应的文件名
5. 放到此目录下

### 方法二: ImageMagick (命令行)

安装 [ImageMagick](https://imagemagick.org/) 后:

```bash
# 生成 Windows 图标
magick convert icon-source.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico

# 生成 Linux 图标
magick convert icon-source.png -resize 512x512 icon.png
```

### 方法三: macOS iconutil

macOS 用户可以使用内置的 iconutil:

```bash
# 1. 创建 iconset 目录
mkdir icon.iconset

# 2. 生成不同尺寸的图标
sips -z 16 16     icon-source.png --out icon.iconset/icon_16x16.png
sips -z 32 32     icon-source.png --out icon.iconset/icon_16x16@2x.png
sips -z 32 32     icon-source.png --out icon.iconset/icon_32x32.png
sips -z 64 64     icon-source.png --out icon.iconset/icon_32x32@2x.png
sips -z 128 128   icon-source.png --out icon.iconset/icon_128x128.png
sips -z 256 256   icon-source.png --out icon.iconset/icon_128x128@2x.png
sips -z 256 256   icon-source.png --out icon.iconset/icon_256x256.png
sips -z 512 512   icon-source.png --out icon.iconset/icon_256x256@2x.png
sips -z 512 512   icon-source.png --out icon.iconset/icon_512x512.png
sips -z 1024 1024 icon-source.png --out icon.iconset/icon_512x512@2x.png

# 3. 生成 icns 文件
iconutil -c icns icon.iconset -o icon.icns

# 4. 清理临时文件
rm -rf icon.iconset
```

### 方法四: GIMP (图形界面)

1. 使用 [GIMP](https://www.gimp.org/) 打开源图片
2. 调整图片大小到所需尺寸
3. 导出为对应格式

## 临时方案

如果暂时没有图标,应用可以正常运行,只是会使用系统默认图标。

## 图标设计建议

1. **简洁明了**: 图标应该简单、易识别
2. **适配多尺寸**: 确保在小尺寸下也清晰可见
3. **透明背景**: PNG 和 ICNS 建议使用透明背景
4. **品牌一致**: 保持与应用品牌风格一致
5. **测试显示**: 在不同背景下测试显示效果

## 示例

一个好的应用图标应该:
- 在 16x16 像素下依然可识别
- 适配暗色和亮色主题
- 有足够的对比度
- 避免过于复杂的细节

## 测试

放置图标后,可以通过以下方式测试:

```bash
# 开发模式下查看效果
pnpm start

# 打包后查看效果
pnpm run build:win
```

打包完成后,查看生成的安装包图标是否正确显示。

