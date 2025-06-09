import os
import cv2
import numpy as np
import math
import random

def create_coin_emoji(text, background_color, text_color=(255, 255, 255), size=512, is_ryo=False):
    """
    Ultra yüksek kaliteli para veya puan emojisi oluşturur.
    
    Args:
        text: Emoji üzerinde gösterilecek metin (KP, TP, IP, EP, RYO)
        background_color: Arka plan rengi (BGR tuple)
        text_color: Metin rengi (BGR tuple)
        size: Emoji boyutu (piksel) - 512x512 varsayılan
        is_ryo: RYO için altın külçe şekli kullanılır
        
    Returns:
        ndarray: Oluşturulan emoji görüntüsü
    """
    # Not: OpenCV BGR formatını kullanır, RGB renklerini değiştiriyoruz
    bg_color = (background_color[2], background_color[1], background_color[0])
    
    # Boyut ve yazı büyüklüğünü ayarla
    img_size = size
    
    # Yazı büyüklüğü ayarla - 512x512 için optimize
    if is_ryo:
        font_size = int(size * 0.35)  # RYO için büyütüldü
    else:
        font_size = int(size * 0.45)  # Diğer kısaltmalar için büyütüldü
    
    # Metin, arka plan ve kenarlık renkleri
    border_color = tuple(max(0, c - 80) for c in bg_color)  # Daha koyu kenarlık
    highlight_color = tuple(min(255, c + 80) for c in bg_color)  # Daha açık vurgu
    
    # Metin rengi - arka planın daha koyu tonu, outline color ile aynı
    text_color = (border_color[0], border_color[1], border_color[2]) 
    
    # Metin vurguları için açık ton - contrast için
    text_highlight = tuple(min(255, c + 50) for c in text_color)
    
    # Şeffaf arka plan ile BGRA görüntüsü oluştur
    img = np.zeros((img_size, img_size, 4), dtype=np.uint8)
    
    # Font dosyasını ayarla
    try:
        # Direkt bu projenin kök dizinini al
        project_root = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(project_root, "data", "fonts", "GothamNarrow-Bold.otf")
        # OpenCV için font ayarları
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = font_size / 30  # OpenCV font ölçeği
        font_thickness = max(1, int(font_size / 25))
    except Exception as e:
        print(f"Font yüklenemedi: {e}")
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = font_size / 30
        font_thickness = max(1, int(font_size / 25))
    
    # Para şekli: RYO için altın külçe, diğerleri için daire
    padding = int(size * 0.08)  # Kenar boşluğu
    
    if is_ryo:
        # RYO için itibari para tasarımı - modernize edilmiş versiyon
        rect_width = img_size - 2 * padding
        rect_height = int(rect_width * 0.55)  # Daha yüksek dikdörtgen
        
        # Dikdörtgen koordinatlarını tanımla
        x0 = padding
        y0 = (img_size - rect_height) // 2
        x1 = img_size - padding
        y1 = y0 + rect_height
        
        # Yuvarlatılmış köşe yarıçapı
        corner_radius = int(rect_height * 0.15)
        
        # Arka plan gölgesi ekleme
        shadow_img = np.zeros((img_size, img_size, 4), dtype=np.uint8)
        shadow_offset = int(size * 0.03)
        
        for i in range(3):
            offset = shadow_offset + i*1
            alpha = 80 - i*20
            
            # Gölge için yuvarlatılmış dikdörtgen çiz
            # OpenCV'de yuvarlatılmış dikdörtgen olmadığı için normal dikdörtgen ve 4 köşe için elipsler çiziyoruz
            shadow_rect = np.zeros((img_size, img_size), dtype=np.uint8)
            cv2.rectangle(shadow_rect, (x0 + offset + corner_radius, y0 + offset), 
                         (x1 + offset - corner_radius, y1 + offset), 255, -1)
            cv2.rectangle(shadow_rect, (x0 + offset, y0 + offset + corner_radius), 
                         (x1 + offset, y1 + offset - corner_radius), 255, -1)
            
            # Yuvarlatılmış köşeler için elipsler
            cv2.ellipse(shadow_rect, (x0 + offset + corner_radius, y0 + offset + corner_radius), 
                       (corner_radius, corner_radius), 0, 90, 180, 255, -1)
            cv2.ellipse(shadow_rect, (x1 + offset - corner_radius, y0 + offset + corner_radius), 
                       (corner_radius, corner_radius), 0, 0, 90, 255, -1)
            cv2.ellipse(shadow_rect, (x0 + offset + corner_radius, y1 + offset - corner_radius), 
                       (corner_radius, corner_radius), 0, 180, 270, 255, -1)
            cv2.ellipse(shadow_rect, (x1 + offset - corner_radius, y1 + offset - corner_radius), 
                       (corner_radius, corner_radius), 0, 270, 360, 255, -1)
            
            # Gölge rengini ve alpha değerini atama
            shadow_color = np.zeros((img_size, img_size, 4), dtype=np.uint8)
            shadow_color[shadow_rect > 0] = [0, 0, 0, alpha]
            
            # Gölgeyi ana gölge görüntüsüne ekle
            shadow_img = cv2.add(shadow_img, shadow_color)
        
        # Gölgeye blur uygula
        shadow_img = cv2.GaussianBlur(shadow_img, (size//25, size//25), 0)
        
        # Gölgeyi ana görüntüye ekle (alpha channel dikkate alarak)
        for c in range(3):  # BGR kanalları
            img[:,:,c] = img[:,:,c] * (1 - shadow_img[:,:,3]/255.0) + shadow_img[:,:,c] * (shadow_img[:,:,3]/255.0)
        img[:,:,3] = np.maximum(img[:,:,3], shadow_img[:,:,3])
        
        # İtibari para tasarımı için renk skalası
        money_top = (136, 184, 206)      # Açık bej (BGR)
        money_middle = (130, 178, 199)   # Orta bej (BGR)
        money_bottom = (124, 170, 191)   # Koyu bej (BGR)
        
        # Kültçe görünümünü oluştur
        gold_bar = np.zeros((img_size, img_size, 4), dtype=np.uint8)
        
        # Yuvarlatılmış dikdörtgen için maske oluştur
        bar_mask = np.zeros((img_size, img_size), dtype=np.uint8)
        cv2.rectangle(bar_mask, (x0 + corner_radius, y0), (x1 - corner_radius, y1), 255, -1)
        cv2.rectangle(bar_mask, (x0, y0 + corner_radius), (x1, y1 - corner_radius), 255, -1)
        
        # Yuvarlatılmış köşeler
        cv2.ellipse(bar_mask, (x0 + corner_radius, y0 + corner_radius), 
                   (corner_radius, corner_radius), 0, 90, 180, 255, -1)
        cv2.ellipse(bar_mask, (x1 - corner_radius, y0 + corner_radius), 
                   (corner_radius, corner_radius), 0, 0, 90, 255, -1)
        cv2.ellipse(bar_mask, (x0 + corner_radius, y1 - corner_radius), 
                   (corner_radius, corner_radius), 0, 180, 270, 255, -1)
        cv2.ellipse(bar_mask, (x1 - corner_radius, y1 - corner_radius), 
                   (corner_radius, corner_radius), 0, 270, 360, 255, -1)
        
        # Gradyan gradient oluştur
        for y in range(y0, y1+1):
            pos = (y - y0) / rect_height
            
            # İtibari para görünümü için üç bölgeli gradiyent
            if pos < 0.4:
                t = pos / 0.4
                b = int(money_top[0] * (1-t) + money_middle[0] * t)
                g = int(money_top[1] * (1-t) + money_middle[1] * t)
                r = int(money_top[2] * (1-t) + money_middle[2] * t)
            else:
                t = (pos - 0.4) / 0.6
                b = int(money_middle[0] * (1-t) + money_bottom[0] * t)
                g = int(money_middle[1] * (1-t) + money_bottom[1] * t)
                r = int(money_middle[2] * (1-t) + money_bottom[2] * t)
            
            # Her satırda hafif desen varyasyonu ekle
            variation = math.sin(y * 0.1) * 3
            b = min(255, max(0, b + int(variation)))
            g = min(255, max(0, g + int(variation)))
            r = min(255, max(0, r + int(variation)))
            
            # Bu satırı boyutlandır
            for x in range(x0, x1+1):
                if bar_mask[y, x] > 0:
                    gold_bar[y, x] = [b, g, r, 255]
        
        # Altın külçeyi ana görüntüye ekle
        for c in range(3):  # BGR kanalları
            img[:,:,c] = img[:,:,c] * (1 - gold_bar[:,:,3]/255.0) + gold_bar[:,:,c] * (gold_bar[:,:,3]/255.0)
        img[:,:,3] = np.maximum(img[:,:,3], gold_bar[:,:,3])
        
        # Kenar dokusu ekle - altın para izlenimi vermek için
        # İnce kenar çizgisi
        border_img = np.zeros((img_size, img_size, 4), dtype=np.uint8)
        
        # Dış kenar çizgisi
        cv2.rectangle(border_img, (x0 + corner_radius, y0), (x1 - corner_radius, y0+2), (0, 117, 139, 180), -1)
        cv2.rectangle(border_img, (x0 + corner_radius, y1-2), (x1 - corner_radius, y1), (0, 117, 139, 180), -1)
        cv2.rectangle(border_img, (x0, y0 + corner_radius), (x0+2, y1 - corner_radius), (0, 117, 139, 180), -1)
        cv2.rectangle(border_img, (x1-2, y0 + corner_radius), (x1, y1 - corner_radius), (0, 117, 139, 180), -1)
        
        # Yuvarlatılmış köşeler için kenar
        cv2.ellipse(border_img, (x0 + corner_radius, y0 + corner_radius), 
                   (corner_radius, corner_radius), 0, 90, 180, (0, 117, 139, 180), 2)
        cv2.ellipse(border_img, (x1 - corner_radius, y0 + corner_radius), 
                   (corner_radius, corner_radius), 0, 0, 90, (0, 117, 139, 180), 2)
        cv2.ellipse(border_img, (x0 + corner_radius, y1 - corner_radius), 
                   (corner_radius, corner_radius), 0, 180, 270, (0, 117, 139, 180), 2)
        cv2.ellipse(border_img, (x1 - corner_radius, y1 - corner_radius), 
                   (corner_radius, corner_radius), 0, 270, 360, (0, 117, 139, 180), 2)
        
        # İç dikdörtgen - altın külçe etkisi
        inner_padding = int(size * 0.03)
        inner_radius = int(rect_height * 0.08)
        
        ix0 = x0 + inner_padding
        iy0 = y0 + inner_padding
        ix1 = x1 - inner_padding
        iy1 = y1 - inner_padding
        
        # İç kenar çizgisi
        cv2.rectangle(border_img, (ix0 + inner_radius, iy0), (ix1 - inner_radius, iy0+1), (0, 223, 255, 100), -1)
        cv2.rectangle(border_img, (ix0 + inner_radius, iy1-1), (ix1 - inner_radius, iy1), (0, 223, 255, 100), -1)
        cv2.rectangle(border_img, (ix0, iy0 + inner_radius), (ix0+1, iy1 - inner_radius), (0, 223, 255, 100), -1)
        cv2.rectangle(border_img, (ix1-1, iy0 + inner_radius), (ix1, iy1 - inner_radius), (0, 223, 255, 100), -1)
        
        # İç yuvarlatılmış köşeler
        cv2.ellipse(border_img, (ix0 + inner_radius, iy0 + inner_radius), 
                   (inner_radius, inner_radius), 0, 90, 180, (0, 223, 255, 100), 1)
        cv2.ellipse(border_img, (ix1 - inner_radius, iy0 + inner_radius), 
                   (inner_radius, inner_radius), 0, 0, 90, (0, 223, 255, 100), 1)
        cv2.ellipse(border_img, (ix0 + inner_radius, iy1 - inner_radius), 
                   (inner_radius, inner_radius), 0, 180, 270, (0, 223, 255, 100), 1)
        cv2.ellipse(border_img, (ix1 - inner_radius, iy1 - inner_radius), 
                   (inner_radius, inner_radius), 0, 270, 360, (0, 223, 255, 100), 1)
        
        # Kenarları ana görüntüye ekle
        for c in range(3):  # BGR kanalları
            img[:,:,c] = img[:,:,c] * (1 - border_img[:,:,3]/255.0) + border_img[:,:,c] * (border_img[:,:,3]/255.0)
        img[:,:,3] = np.maximum(img[:,:,3], border_img[:,:,3])
        
        # Altın dokusu ekleme
        texture_img = np.zeros((img_size, img_size, 4), dtype=np.uint8)
        
        # Rastgele altın doku noktaları
        for _ in range(rect_width * rect_height // 20):
            tx = random.randint(x0 + 10, x1 - 10)
            ty = random.randint(y0 + 10, y1 - 10)
            
            # Altın parlaması
            size_var = random.randint(1, 3)
            brightness = random.uniform(0.9, 1.2)
            
            # BGR + Alpha
            sparkle_color = (
                int(min(255, 0 * brightness)),        # B
                int(min(255, 223 * brightness)),      # G
                int(min(255, 255 * brightness)),      # R
                50                                     # Alpha
            )
            
            cv2.circle(texture_img, (tx, ty), size_var, sparkle_color, -1)
        
        # Dokuya blur uygula
        texture_img = cv2.GaussianBlur(texture_img, (3, 3), 0.8)
        
        # Dokuyu ana görüntüye ekle
        for c in range(3):  # BGR kanalları
            img[:,:,c] = img[:,:,c] * (1 - texture_img[:,:,3]/255.0) + texture_img[:,:,c] * (texture_img[:,:,3]/255.0)
        img[:,:,3] = np.maximum(img[:,:,3], texture_img[:,:,3])
        
        # RYO metin ekleme
        letters = ["R", "Y", "O"]
        symbol_size = int(size * 0.32)  # RYO harfleri için büyütüldü
        text_color_bgr = (0, 67, 80)    # BGR formatında koyu altın rengi
        
        # Metin genişliğini ve pozisyonunu hesapla
        letter_width = int(symbol_size * 0.6)  # Yaklaşık harf genişliği
        total_width = letter_width * len(letters) + (len(letters) - 1) * 10
        symbol_x = (img_size - total_width) // 2
        symbol_y = img_size // 2 + symbol_size // 3  # Dikey ortalama için y ofset
        
        # Metin katmanı
        text_img = np.zeros((img_size, img_size, 4), dtype=np.uint8)
        
        # Her harfi aralıklarla çiz
        for letter in letters:
            # Her harf için gölge efekti
            shadow_depth = 4
            for offset in range(1, shadow_depth + 1):
                alpha = 180 - 30 * offset
                shadow_color = (0, 0, 0, alpha)
                
                cv2.putText(text_img, letter, 
                           (symbol_x + offset, symbol_y + offset), 
                           font, font_scale * 1.5, shadow_color, 
                           font_thickness, cv2.LINE_AA)
            
            # Ana metni çiz
            cv2.putText(text_img, letter, 
                       (symbol_x, symbol_y), 
                       font, font_scale * 1.5, 
                       (text_color_bgr[0], text_color_bgr[1], text_color_bgr[2], 255), 
                       font_thickness, cv2.LINE_AA)
            
            # Sonraki harf pozisyonu
            symbol_x += letter_width + 10
        
        # Metin katmanına blur uygula
        text_img = cv2.GaussianBlur(text_img, (3, 3), 0.5)
        
        # Metni ana görüntüye ekle
        for c in range(3):  # BGR kanalları
            img[:,:,c] = img[:,:,c] * (1 - text_img[:,:,3]/255.0) + text_img[:,:,c] * (text_img[:,:,3]/255.0)
        img[:,:,3] = np.maximum(img[:,:,3], text_img[:,:,3])
        
    else:
        # Diğer para birimleri için daire şekli - gerçekçi madeni para
        radius = (img_size - 2 * padding) // 2
        center_x = img_size // 2
        center_y = img_size // 2
        
        # 3D görünüm için alt gölge
        shadow_img = np.zeros((img_size, img_size, 4), dtype=np.uint8)
        shadow_offset = int(size * 0.025)
        
        # Çoklu gölge katmanları
        for i in range(4):
            offset = shadow_offset + i*2
            alpha = 100 - i*15
            shadow_circle = np.zeros((img_size, img_size), dtype=np.uint8)
            cv2.circle(shadow_circle, (center_x + offset, center_y + offset), 
                      radius, 255, -1)
            
            shadow_color = np.zeros((img_size, img_size, 4), dtype=np.uint8)
            shadow_color[shadow_circle > 0] = [0, 0, 0, alpha]
            
            shadow_img = cv2.add(shadow_img, shadow_color)
        
        # Gölgeye blur uygula
        shadow_img = cv2.GaussianBlur(shadow_img, (size//15, size//15), 0)
        
        # Gölgeyi ana görüntüye ekle
        for c in range(3):
            img[:,:,c] = img[:,:,c] * (1 - shadow_img[:,:,3]/255.0) + shadow_img[:,:,c] * (shadow_img[:,:,3]/255.0)
        img[:,:,3] = np.maximum(img[:,:,3], shadow_img[:,:,3])
        
        # Dış kenar dairesi - kalın
        cv2.circle(img, (center_x, center_y), radius + 6, 
                  (border_color[0], border_color[1], border_color[2], 255), -1)
        
        # Ana daire
        cv2.circle(img, (center_x, center_y), radius, 
                  (bg_color[0], bg_color[1], bg_color[2], 255), -1)
        
        # Madeni para dokusu
        texture_img = np.zeros((img_size, img_size, 4), dtype=np.uint8)
        
        # Dairesel gradyan temel doku
        for r in range(radius, 0, -1):
            # Merkezden uzaklığa göre renk değişimi
            dist = r / radius
            brightness = 0.8 + 0.4 * (1 - dist**2)  # Merkeze yakın daha parlak
            
            # Dairenin bu yarıçaptaki rengini hesapla
            b = int(min(255, bg_color[0] * brightness))
            g = int(min(255, bg_color[1] * brightness))
            r_val = int(min(255, bg_color[2] * brightness))
            
            # Dairesel çizgi çiz
            cv2.circle(texture_img, (center_x, center_y), r, 
                      (b, g, r_val, 50), 1, cv2.LINE_AA)
        
        # Rastgele metal doku noktaları
        coin_mask = np.zeros((img_size, img_size), dtype=np.uint8)
        cv2.circle(coin_mask, (center_x, center_y), int(radius * 0.95), 255, -1)
        
        for _ in range(size):
            # Rastgele bir açı ve yarıçap seç
            angle = random.uniform(0, 2 * math.pi)
            r = random.uniform(0, radius * 0.95)
            
            # Koordinatları hesapla
            x = center_x + int(r * math.cos(angle))
            y = center_y + int(r * math.sin(angle))
            
            # Nokta koordinatları daire içinde mi kontrol et
            if coin_mask[y, x] > 0:
                # Rastgele parlaklık
                brightness = random.uniform(0.85, 1.15)
                b = int(min(255, bg_color[0] * brightness))
                g = int(min(255, bg_color[1] * brightness))
                r_val = int(min(255, bg_color[2] * brightness))
                
                # Nokta büyüklüğü
                point_size = random.randint(1, 3)
                
                # Noktayı çiz
                cv2.circle(texture_img, (x, y), point_size, 
                          (b, g, r_val, 80), -1, cv2.LINE_AA)
        
        # Dokuya blur uygulayarak yumuşat
        texture_img = cv2.GaussianBlur(texture_img, (3, 3), 0.7)
        
        # Dokuyu ana görüntüye ekle
        for c in range(3):
            img[:,:,c] = img[:,:,c] * (1 - texture_img[:,:,3]/255.0) + texture_img[:,:,c] * (texture_img[:,:,3]/255.0)
        img[:,:,3] = np.maximum(img[:,:,3], texture_img[:,:,3])
        
        # İç kenar dairesi - madeni para detayı
        inner_radius = int(radius * 0.88)
        cv2.circle(img, (center_x, center_y), inner_radius, 
                  (border_color[0], border_color[1], border_color[2], 200), 3)
        
        # Madeni para yüzeyindeki parlamalar - metal efekti
        shine_img = np.zeros((img_size, img_size, 4), dtype=np.uint8)
        
        # Ana parlama - açılı ışık efekti
        shine_angle = math.pi / 4  # 45 derece
        
        for r in range(1, radius+1):
            for angle_offset in range(-30, 31):
                angle = shine_angle + math.radians(angle_offset/10)
                
                # Açıdan uzaklığa göre parlaklık
                angle_factor = 1.0 - abs(angle_offset) / 30
                
                # Yarıçaptan uzaklığa göre parlaklık
                radius_factor = 1.0 - abs(r - radius*0.6) / (radius*0.6)
                
                # Toplam parlaklık faktörü
                total_factor = angle_factor * radius_factor
                if total_factor < 0.1:
                    continue
                
                # Koordinatları hesapla
                x = center_x + int(r * math.cos(angle))
                y = center_y - int(r * math.sin(angle))
                
                # Bu noktanın daire içinde olup olmadığını kontrol et
                if (x - center_x)**2 + (y - center_y)**2 <= radius**2:
                    # Parlaklık değeri
                    alpha = int(100 * total_factor)
                    
                    # Parlama rengini hesapla (BGR)
                    b = int(min(255, highlight_color[0]))
                    g = int(min(255, highlight_color[1]))
                    r_val = int(min(255, highlight_color[2]))
                    
                    # Noktayı çiz
                    shine_img[y, x] = [b, g, r_val, alpha]
        
        # Parlamaya blur uygula
        shine_img = cv2.GaussianBlur(shine_img, (5, 5), 2)
        
        # Parlamayı ana görüntüye ekle
        for c in range(3):
            img[:,:,c] = img[:,:,c] * (1 - shine_img[:,:,3]/255.0) + shine_img[:,:,c] * (shine_img[:,:,3]/255.0)
        img[:,:,3] = np.maximum(img[:,:,3], shine_img[:,:,3])
        
        # Metni hazırla
        text_size, _ = cv2.getTextSize(text, font, font_scale * 1.8, font_thickness)
        text_x = (img_size - text_size[0]) // 2
        text_y = (img_size + text_size[1]) // 2
        
        # Metin katmanı
        text_img = np.zeros((img_size, img_size, 4), dtype=np.uint8)
        
        # Gölge efekti
        shadow_depth = 4
        for offset in range(1, shadow_depth + 1):
            alpha = 180 - 30 * offset
            shadow_color = (0, 0, 0, alpha)
            
            cv2.putText(text_img, text, 
                       (text_x + offset, text_y + offset), 
                       font, font_scale * 1.8, shadow_color, 
                       font_thickness, cv2.LINE_AA)
        
        # Parlak kenar vurguları
        for offset in range(-2, 0):
            for y_offset in range(-2, 0):
                dist = math.sqrt(offset**2 + y_offset**2) / 2
                alpha = int(100 * (1 - dist))
                
                b = int(min(255, text_highlight[0]))
                g = int(min(255, text_highlight[1]))
                r_val = int(min(255, text_highlight[2]))
                
                cv2.putText(text_img, text, 
                           (text_x + offset, text_y + y_offset), 
                           font, font_scale * 1.8, 
                           (b, g, r_val, alpha), 
                           font_thickness, cv2.LINE_AA)
        
        # Ana metin
        cv2.putText(text_img, text, 
                   (text_x, text_y), 
                   font, font_scale * 1.8, 
                   (text_color[0], text_color[1], text_color[2], 255), 
                   font_thickness, cv2.LINE_AA)
        
        # Metin katmanına blur uygula
        text_img = cv2.GaussianBlur(text_img, (3, 3), 0.5)
        
        # Metni ana görüntüye ekle
        for c in range(3):
            img[:,:,c] = img[:,:,c] * (1 - text_img[:,:,3]/255.0) + text_img[:,:,c] * (text_img[:,:,3]/255.0)
        img[:,:,3] = np.maximum(img[:,:,3], text_img[:,:,3])
    
    # Son rötuşlar - görüntü kalitesini artır
    
    # Keskinlik ve kontrast ayarlarını OpenCV ile uygula
    # Not: OpenCV'de direkt kontrast artırma için alpha değeri kullanılır
    alpha = 1.3  # Kontrast faktörü (1.0 = orijinal)
    beta = 10    # Parlaklık faktörü (0 = orijinal)
    
    # Görüntü işleme - alfa kanalını koruyarak
    alpha_channel = img[:, :, 3].copy()
    rgb_img = img[:, :, :3].copy()
    
    # Kontrast ve parlaklık ayarı
    rgb_img = cv2.convertScaleAbs(rgb_img, alpha=alpha, beta=beta)
    
    # Keskinleştirme - unsharp masking
    gaussian = cv2.GaussianBlur(rgb_img, (0, 0), 3)
    rgb_img = cv2.addWeighted(rgb_img, 1.5, gaussian, -0.5, 0)
    
    # Hafif bulanıklaştırma - çok keskin kenarları yumuşatmak için
    rgb_img = cv2.GaussianBlur(rgb_img, (3, 3), 0.4)
    
    # Alfa kanalını geri ekle
    img[:, :, :3] = rgb_img
    img[:, :, 3] = alpha_channel
    
    # Boyutu küçültme gerekiyorsa yeniden boyutlandır
    if size != 512:
        img = cv2.resize(img, (size, size), interpolation=cv2.INTER_LANCZOS4)
    
    return img

def generate_all_currency_emojis(output_dir="data/currency_emojis"):
    """
    Tüm para ve puan emojilerini oluşturup kaydeder
    """
    try:
        # Proje kök dizininden data/currency_emojis klasörüne kaydet
        project_root = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(project_root, output_dir)
        os.makedirs(output_path, exist_ok=True)
        
        print(f"Emojiler şu klasöre kaydedilecek: {output_path}")
    except Exception as e:
        print(f"Klasör oluşturma hatası: {e}")
        return
    
    # Para birimleri ve renkleri - en iyi metal renkleri (BGR değil, RGB olarak tutuyoruz)
    currencies = {
        "KP": (60, 130, 220),   # Parlak mavi-gümüş
        "TP": (230, 160, 50),   # Zengin bronz
        "IP": (90, 200, 100),   # Canlı yeşil
        "EP": (190, 80, 190),   # Zengin mor
        "RYO": (250, 210, 60)   # Parlak altın
    }
    
    # Her para birimi için emoji oluştur ve kaydet
    for curr, color in currencies.items():
        print(f"{curr} emojisi oluşturuluyor...")
        
        # Dosya isimleri
        full_filename = os.path.join(output_path, f"{curr.lower()}_emoji.png")
        small_filename = os.path.join(output_path, f"{curr.lower()}_emoji_small.png")
        
        # Eğer dosyalar zaten varsa atla
        if os.path.exists(full_filename) and os.path.exists(small_filename):
            print(f"✓ {curr} emojileri zaten mevcut, atlanıyor...")
            continue
        
        # Yoksa yeni emoji oluştur
        is_ryo = (curr == "RYO")
        img = create_coin_emoji(curr, color, is_ryo=is_ryo)
        
        # Tam boyutlu versiyonu kaydet
        if not os.path.exists(full_filename):
            # OpenCV BGR formatını PNG'ye kaydederken dikkat etmeliyiz
            # cv2.imwrite alfa kanalını destekler ama BGRA formatındadır
            cv2.imwrite(full_filename, img)
            print(f"✓ Tam boyutlu emoji oluşturuldu: {full_filename}")
        
        # Discord için küçük versiyon
        if not os.path.exists(small_filename):
            small_img = cv2.resize(img, (128, 128), interpolation=cv2.INTER_LANCZOS4)
            cv2.imwrite(small_filename, small_img)
            print(f"✓ Discord için optimize edilmiş emoji oluşturuldu: {small_filename}")

# Eğer dosya doğrudan çalıştırılıyorsa, tüm emojileri oluştur
if __name__ == "__main__":
    print("Ultra yüksek kaliteli para emojileri oluşturuluyor... (512x512)")
    generate_all_currency_emojis()
    print("İşlem tamamlandı! Hem tam boyutlu (512x512) hem de Discord uyumlu (128x128) emojiler oluşturuldu.")
