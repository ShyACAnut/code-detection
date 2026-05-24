import os
import json
import subprocess
import tempfile
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import anyio

app = Server("report-converter")

@app.list_tools()
async def list_tools():
    return [
        {
            "name": "convert_to_pdf",
            "description": "将 Markdown 内容转换为 PDF 文件（使用reportlab库，无需pandoc）",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "markdown": {"type": "string", "description": "Markdown 格式的报告内容"},
                    "filename": {"type": "string", "description": "输出文件名（不含扩展名）"}
                },
                "required": ["markdown", "filename"]
            }
        },
        {
            "name": "convert_to_word",
            "description": "将 Markdown 内容转换为 Word 文档（需要pandoc）",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "markdown": {"type": "string"},
                    "filename": {"type": "string"}
                },
                "required": ["markdown", "filename"]
            }
        }
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "convert_to_pdf":
        return convert_markdown(arguments["markdown"], arguments["filename"], "pdf")
    elif name == "convert_to_word":
        return convert_markdown(arguments["markdown"], arguments["filename"], "docx")
    raise ValueError(f"Unknown tool: {name}")

def convert_markdown(md_content: str, filename: str, output_format: str):
    output_path = f"{filename}.{output_format}"

    # 对于PDF格式，优先使用纯Python的reportlab库
    if output_format == "pdf":
        try:
            from pdf_generator import markdown_to_pdf, check_pdf_capability
            capability = check_pdf_capability()

            if capability["can_generate_pdf"]:
                success = markdown_to_pdf(
                    md_content,
                    output_path,
                    title=f"报告 - {filename}"
                )

                if success and os.path.exists(output_path):
                    result = {"success": True, "file_path": output_path, "method": "reportlab"}
                    return [{"type": "text", "text": json.dumps(result)}]
                else:
                    print(f"[MCP] reportlab生成PDF失败，尝试pandoc")

        except ImportError:
            print("[MCP] pdf_generator模块未找到，尝试pandoc")
        except Exception as e:
            print(f"[MCP] reportlab生成PDF失败: {e}")

    # 如果reportlab不可用或失败，尝试使用pandoc
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write(md_content)
        md_path = f.name

    try:
        cmd = ["pandoc", md_path, "-o", output_path]
        subprocess.run(cmd, check=True, capture_output=True)
        result = {"success": True, "file_path": output_path, "method": "pandoc"}
    except Exception as e:
        result = {"success": False, "error": str(e), "method": "failed"}
    finally:
        if os.path.exists(md_path):
            os.unlink(md_path)  # 删除临时 Markdown 文件

    return [{"type": "text", "text": json.dumps(result)}]

async def main():
    async with anyio.create_task_group() as tg:
        await app.run_stdio_async()

if __name__ == "__main__":
    anyio.run(main)