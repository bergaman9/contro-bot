import os

def read_markdown_file(filename, content_dir='contents'):
    """Markdown dosyasını okur ve içeriğini string olarak döndürür"""
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), content_dir, f"{filename}.md")
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        return f"Dosya bulunamadı: {file_path}"

def load_content(filename, section_index=None, content_dir='contents'):
    """
    Markdown dosyasını yükler ve --- ile ayrılmış bölümlere ayırır
    
    Args:
        filename: Markdown dosyasının adı (.md uzantısı olmadan)
        section_index: İstenen bölümün indeksi (None ise tüm içeriği döndürür)
        content_dir: İçerik dizini (varsayılan: 'contents')
        
    Returns:
        String: İstenen bölümün içeriği veya tüm içerik
    """
    content = read_markdown_file(filename, content_dir)
    sections = content.split("---")
    
    # İçeriği temizle
    sections = [section.strip() for section in sections]
    
    # İstenen bölümü döndür
    if section_index is not None:
        if 0 <= section_index < len(sections):
            return sections[section_index]
        else:
            return f"Bölüm bulunamadı: {section_index}"
    else:
        return content
