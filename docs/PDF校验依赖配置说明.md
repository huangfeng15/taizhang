# PDF校验依赖配置说明

## 问题背景

系统的PDF导入功能使用`python-magic`和`PyPDF2`进行文件安全校验：
- `python-magic`：检测文件MIME类型,防止伪装文件
- `PyPDF2`：校验PDF结构完整性

## Windows系统配置方案

### 问题原因

原`requirements.txt`使用`python-magic==0.4.27`,但该包在Windows上需要额外安装C库`libmagic`,否则会报错：
```
ImportError: failed to find libmagic. Check your installation
```

### 解决方案

**使用`python-magic-bin`替代**
- `python-magic-bin`包含Windows预编译的二进制文件
- 无需额外配置,开箱即用
- 完全兼容`python-magic`的API

### 配置步骤

1. **修改依赖文件**
```diff
# requirements.txt
- python-magic==0.4.27
+ python-magic-bin==0.4.14
```

2. **重新安装依赖**
```bash
pip uninstall -y python-magic
pip install python-magic-bin==0.4.14
```

3. **验证安装**
```bash
python -c "import magic; import PyPDF2; print('Dependencies OK')"
```

## 代码兼容性

`pdf_import/views.py`中的校验代码无需修改,因为两个包的API完全相同：
```python
import magic  # 自动使用python-magic-bin
import PyPDF2

def validate_pdf_file(uploaded_file):
    # MIME类型检测
    file_type = magic.from_buffer(header, mime=True)
    
    # PDF结构校验
    reader = PyPDF2.PdfReader(uploaded_file)
    if not reader.pages:
        raise ValidationError("PDF文件内容为空")
```

## 配置验证

已完成配置验证：
- ✅ `python-magic-bin==0.4.14`已安装
- ✅ `PyPDF2==3.0.1`已安装
- ✅ 导入测试通过
- ✅ 代码无需修改

## 注意事项

1. **Linux/Mac系统**：如需在Linux或Mac部署,需恢复使用`python-magic`,因为这些系统通常预装了`libmagic`库

2. **依赖锁定**：建议在生产环境使用`pip freeze > requirements-lock.txt`锁定所有依赖版本

3. **安全更新**：定期检查`PyPDF2`和`python-magic-bin`的安全更新

## 相关文件

- `requirements.txt` - 依赖声明文件
- `pdf_import/views.py` - PDF校验实现代码
- 第30-65行 `validate_pdf_file()` 函数

## 更新记录

- 2025-11-17：将`python-magic`替换为`python-magic-bin`,解决Windows安装问题