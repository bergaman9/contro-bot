- Genel olarak Discord sunucusundaki özellikleri listeledim. Bazı özelliklerin nasıl kullanıldığını anlatan yazılar da ekledim.

**Roller**
- Rolleri yönetim ekibi rolleri, özel üye rolleri, level rolleri, üye rolleri olarak sınıflandırabiliriz.
- **Yönetim ekibi** rolleri sunucunun moderasyonundan sorumludur. Sunucuya belli derecelerde müdahale edebilme yetkileri bulunur.
- **Özel** roller ise VIP, Yayıncı, Ekip, Partner gibi rollerdir. Bu roller sunucuya katkıda bulunan üyelere verilir.
- **Level** rolleri ise sunucuda aktif olan üyelere verilir. 

**Kanal İzinleri**
- Önemli botların sorunsuz çalışması ve tüm kanalları izleyebilmesi için admin rollerini kaldırmadım. Bazı botları üye listesinde kalabalık etmesin diye gizledim. Botları {bot} rolünde toplama sebebim bunun kontrolünü kolayca sağlamak içindir.

**Geçici Kanallar**
- <@715621848489918495> ile kontrol edilir. {temporary} bir geçici kanal oluşturma kanalıdır. 
- Bu kanalların herhangi bir moderatöre ihtiyaç duymadan kanalı oluşturan üyeler tarafından yönetilmesi gibi bir avantajı vardır. 
- Mesela geçici kanal oluşturan kişi `/vc limit 5` komutunu yazarsa kanalda 5 kişi olabilir.

**Yayın Kanalları**
- Yayın duyuruları <@375805687529209857> yardımıyla açılan {streams} kanalında duyurulur.

**Müzik ve Radyo**
- Müzik kanalları için ayrı kategori oluşturdum. Bu kanallarda üyeler konuşamaz, sadece müzik dinler ve kanala müzik botunu çekebilirler.
- Discord müzik botlarını engellemeye başladığından dolayı bazı özel botlar bu işlevi yerine getirebiliyor. `/play [şarkı ismi]` komutunu kullanabilirsiniz.
- <@369208607126061057> radyo botudur ve belirtilen radyo kaynağını 7/24 çalar.

**İstatistikler**
- <@491769129318088714> ile kontrol edilir. `<@537011515014774785> topgames` komutu ise sunucuda oynanan oyunların istatistik bilgisini verir.

**Güvenlik Sistemi**
- Sunucu güvenliğini <@536991182035746816> bot sağlar. Herhangi bir moderatör bir dakika içerisinde 5 üye banlarsa yetkisi elinden otomatik olarak alınır. Üst yetkili biri sunucuda değilken sunucuya zarar vermesi bot sayesinde engellenir. Buna benzer kanal oluşturma ve silme, rol oluşturma ve silme için de limitler bulunmaktadır.
- Otomatik moderasyon modülünü de açtım. Otomatik olarak linkleri vs. engelleyecek.
- <@689766089567109158> ile Türkçe küfürler engelleniyor.

**Level Sistemi**
- <@282859044593598464> ile kontrol edilir. Çünkü sesteki aktivitenizi de takip edip rol verebiliyor. Sadece yazı kanallarında yazdıklarınıza göre rol vermiyor ancak ayar yapılabiliyor.
  → https://probot.io/server/{guild_id} sitesinden ayarlar düzenlenebilir.

## Sunucu Özellikleri - Sayfa 2

**Botlar**
- Sunucudaki her botun bir işlevi var. Aşağıda eklediğim bazı botların özelliğinden bahsettim. 
  → <@674885857458651161> ile üye istatistik tabloları çıkarabilirsiniz.
  → <@936929561302675456> ile AI çizim yaptırabilirsiniz. `/imagine prompt:`
  → @Craig#1289 ses kaydetmek içindir. `/join`
  → `/poll create` komutu ile anket oluşturabilirsiniz.

**DM Mesajlar**
- Biri sunucuya katıldığında <@235148962103951360> yardımıyla üyeye kısa bilgilendirici bir hoş geldin mesajı gönderiliyor.
- Üye sunucuda level rolü aldığında da DM mesaj gönderiliyor.

**Moderasyon Komutları**
- Sunucuda yetkisi olanların kullanabileceği komutlardır.
  → Mesajları silme yetkisi olan ya da üyeleri kickleme ve banlama yetkisi olanlar `/clear amount:` ya da `/purge all count:` yazarak kanaldaki belirttiği mesaj adeti kadar mesajı siler.
  → `!avatar` ve `!serverinfo` gibi faydalı komutlar da bulunuyor. Discord hepsini ezberde tutmayalım diye slash komutlar özelliğini getirdi. / yazınca destekleyen botların komutlarını görebiliyorsunuz.
  → Bazı moderasyon komutları, kickleme ve banlama gibi, fare hareketleriyle kolayca yapılabildiğinden komutla yapmanıza gerek yok ama illa bir komut kullanacaksanız güvenlik botu olan <@536991182035746816> botun moderasyon komutlarını kullanabilirsiniz. `w!ban @user` ya da `/ban add @user` gibi.

**Çekiliş Sistemi**
- {giveaways} kanalında `/giveaway create` komutu ile çekiliş oluşturabilirsiniz. <@155149108183695360> bu iş için gördüğüm en iyi bot, çünkü katılımcıları roller ile kısıtlamak isterseniz bunu başarılı bir şekilde yapıyor ve çekilişlerin özelleştirilebilmesi için şu anda premium şart koşmuyor.
- Discord botlarında görmediğim özellikleri custom komut olarak kendi botuma ekliyorum. Belli bir limite gelince çekilişi bitirmesi için botuma eklediğim `/giveaway create limit: prize:` komutunu kullanabilirsiniz.

**Disboard**
- Sunucunuzun internetten üye çekebilmesi için [disboard.org](https://disboard.org/) gibi sitelerde olmalıdır. `/bump` komutuyla site üzerinde öne çıkarılır, siteye göz atan kullanıcılar sunucuya katılabilir. Daha sonraları isterseniz top.gg ve discord.me gibi sitelere de ekleyebilirsiniz.
  → https://disboard.org/server/{guild_id} sitesinde sunucunuzu görebilirsiniz.

**Ticket Sistemi**
- {support} kanalından üyeler ticket oluşturarak sunucuda özel destek kanalları oluşturabilir. Yetkililer bu kanallarda üyelere yardımcı olur ve kanalı yönetebilirler.

**Emoji Kopyalamak**
- Discord Nitro sahibiyseniz <@696870234262339614> sayesinde `/emoji steal [emoji]` ile emoji kopyalayabilirsiniz.

**Oyunlar**
- <@402528814548254720> sayesinde oyun güncellemeleri {games} kanalında paylaşılıyor. Dashboard üzerinden oyunlar açılıp kapatılabilir.
- <@672822334641537041> sayesinde bedava oyun duyuruları yapılıyor.

**Eğlence Komutları**
- `/meme` `/movie [film ismi]` `/youtube` en faydalı gördüğüm eğlence komutlarıdır. Daha bir sürü gerekli gereksiz komutlar var, botları kurcalayarak yenilerini keşfedebilirsiniz.

**Sunucu Kayıtları**
- Sunucu ile ilgili hareketleri takip edebileceğiniz kanalları ayarladım.
