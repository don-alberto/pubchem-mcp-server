# PubChem MCP Server (Python版本)

这是一个用Python实现的Model Context Protocol (MCP)服务器，提供PubChem化合物数据检索功能。

## 功能

- 通过化合物名称或PubChem CID检索化合物数据
- 支持多种输出格式：JSON、CSV和XYZ
- 支持3D结构数据检索（XYZ格式）
- 提供命令行接口和MCP服务器接口

## 安装

### 基本安装

```bash
# 从源代码安装
git clone https://github.com/yourusername/pubchem-mcp-server.git
cd pubchem-mcp-server/python_version
pip install .

# 或者直接从PyPI安装（如果已发布）
pip install pubchem-mcp-server
```

### 安装RDKit支持（可选）

RDKit用于增强3D结构生成功能，但不是必需的：

```bash
pip install "pubchem-mcp-server[rdkit]"
```

或者，您可以单独安装RDKit：

```bash
conda install -c conda-forge rdkit
# 或
pip install rdkit
```

## 使用方法

### 命令行接口

```bash
# 基本用法
pubchem-mcp aspirin

# 指定输出格式
pubchem-mcp aspirin --format CSV

# 获取3D结构（XYZ格式）
pubchem-mcp aspirin --format XYZ --include-3d

# 查看帮助
pubchem-mcp --help
```

### 作为MCP服务器

1. 启动服务器：

```bash
pubchem-mcp-server
```

2. 将服务器添加到MCP配置文件中（通常位于`~/.claude-dev/settings/cline_mcp_settings.json`或`~/Library/Application Support/Claude/claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "pubchem": {
      "command": "python",
      "args": ["-m", "pubchem_mcp_server.server"],
      "env": {},
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

3. 重启Claude应用程序或Claude开发环境，然后您就可以使用PubChem MCP工具了。

## API

### 主要函数

- `get_pubchem_data(query, format='JSON', include_3d=False)`: 获取PubChem化合物数据
- `get_xyz_structure(cid, smiles, compound_info)`: 获取化合物的XYZ格式3D结构

## 依赖项

- Python >= 3.8
- requests >= 2.25.0
- MCP SDK（可选，用于MCP服务器功能）
- rdkit >= 2022.9.1（可选，用于增强3D结构生成功能）

### 关于MCP SDK

MCP SDK是Model Context Protocol的软件开发工具包，用于创建MCP服务器。由于MCP SDK可能不在PyPI上公开可用，您可能需要手动安装它。如果您只想使用命令行接口来检索PubChem数据，则不需要安装MCP SDK。

## 许可证

MIT

## 致谢

- PubChem数据由美国国家生物技术信息中心(NCBI)提供
- 基于原始TypeScript版本的PubChem MCP服务器重新实现
