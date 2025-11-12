# ApexCharts 本地备用库

## 问题说明

当 CDN 无法访问时，系统会自动尝试加载本地的 ApexCharts 库文件。

## 手动下载步骤

如果您的网络环境无法访问外部 CDN，请按以下步骤手动下载：

### 方法一：通过浏览器下载

1. 在可以访问外网的电脑上，打开浏览器访问：
   ```
   https://cdn.jsdelivr.net/npm/apexcharts@3.45.0/dist/apexcharts.min.js
   ```

2. 保存该文件到本目录，命名为 `apexcharts.min.js`

### 方法二：通过 npm 安装（如果有 Node.js 环境）

```bash
# 在项目根目录执行
npm install apexcharts@3.45.0

# 复制文件到本目录
copy node_modules\apexcharts\dist\apexcharts.min.js project\static\js\vendor\
```

### 方法三：使用备用 CDN 源

如果主 CDN 不可用，可以尝试：
- https://unpkg.com/apexcharts@3.45.0/dist/apexcharts.min.js
- https://cdn.bootcdn.net/ajax/libs/apexcharts/3.45.0/apexcharts.min.js

## 验证

文件下载完成后，确保文件大小约为 500KB 左右，然后重启应用即可。

## 当前状态

- [x] 目录已创建
- [ ] ApexCharts 文件待下载

下载完成后请删除本说明文件。