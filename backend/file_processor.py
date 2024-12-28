import os
from typing import Union
from fastapi import UploadFile
import PyPDF2
from docx import Document
import magic
import base64

async def process_file(file: UploadFile) -> Union[str, None]:
    try:
        # Read the file content
        content = await file.read()

        # Detect file type
        file_type = magic.from_buffer(content, mime=True)

        # Reset file cursor
        await file.seek(0)

        # Create temp directory if it doesn't exist
        os.makedirs('temp', exist_ok=True)
        temp_path = os.path.join('temp', f"temp_{file.filename}")

        try:
            # Try to decode as text first, regardless of mime type
            try:
                return content.decode('utf-8')
            except UnicodeDecodeError:
                # If it's not text, continue with other formats
                pass

            # Handle PDF files
            if file_type == 'application/pdf':
                with open(temp_path, 'wb') as f:
                    f.write(content)

                text = ""
                with open(temp_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                return text.strip()

            # Handle Word documents
            elif file_type in [
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            ]:
                with open(temp_path, 'wb') as f:
                    f.write(content)

                doc = Document(temp_path)
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                return text.strip()

            # For other files, return file info and first few lines if possible
            else:
                file_info = (
                    f"File Information:\n"
                    f"Filename: {file.filename}\n"
                    f"File type: {file_type}\n"
                    f"File size: {len(content)} bytes\n"
                    f"First 256 bytes (hex): {content[:256].hex()}\n\n"
                )

                # Try to show first few lines if it might be text
                try:
                    first_lines = content[:1024].decode('utf-8')
                    return f"{file_info}File Preview:\n{first_lines}"
                except UnicodeDecodeError:
                    return f"{file_info}[Binary content]"

        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return f"Error processing file: {str(e)}\n\nFile type: {file_type}\nSize: {len(content)} bytes"
