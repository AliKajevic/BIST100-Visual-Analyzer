import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime, timedelta
import yfinance as yf
from pymongo import MongoClient, UpdateOne
from tkcalendar import DateEntry
import threading
import sys
import traceback
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd

class BIST100Dashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("BIST 100 Veri Çekme ve Grafik Uygulaması")
        self.root.geometry("1400x900")
        
        # MongoDB bağlantı değişkenleri
        self.mongo_client = None
        self.db = None
        self.collection = None
        
        # BIST 100 hisse kodları
        self.bist100_stocks = [
            "AKBNK", "ALARK", "ARCLK", "ASELS", "BIMAS", "DOHOL", "EKGYO",
            "ENJSA", "EREGL", "FROTO", "GARAN", "GUBRF", "HALKB", "ISCTR",
            "KCHOL", "KONTR", "KOZAA", "KOZAL", "KRDMD", "MGROS", "ODAS",
            "PETKM", "PGSUS", "SAHOL", "SASA", "SISE", "SOKM", "TAVHL",
            "TCELL", "THYAO", "TKFEN", "TOASO", "TTKOM", "TUPRS", "VAKBN",
            "VESTL", "YKBNK", "AEFES", "AGHOL", "AHGAZ", "AKCNS", "AKSA",
            "ALGYO", "ANHYT", "ANSGR", "ASUZU", "AYDEM", "BASGZ", "BJKAS",
            "BRSAN", "BUCIM", "CANTE", "CCOLA", "CEMTS", "CIMSA", "CVKMD",
            "DOAS", "EGEEN", "ENKAI", "GENIL", "GLYHO", "GOODY", "GOZDE",
            "GSDHO", "HEKTS", "ISGSY", "KARTN", "KLKIM", "KLRHO", "KMPUR",
            "KONKA", "KONYA", "KORDS", "KTSKR", "LOGO", "MAVI", "MPARK",
            "NETAS", "NTHOL", "OTKAR", "OYAKC", "OZKGY", "PAPIL", "RGYAS",
            "SELEC", "SNGYO", "TMSN", "TKNSA", "TOASO", "TRGYO", "TSKB",
            "TTRAK", "TURSG", "ULKER", "ULUUN", "VKGYO", "YEOTK", "ZOREN"
        ]
        
        self.setup_ui()
    
    def setup_ui(self):
        # Ana container - Sol ve Sağ paneller
        main_container = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        main_container.pack(fill="both", expand=True)
        
        # SOL PANEL - Kontroller
        left_panel = tk.Frame(main_container, width=600)
        main_container.add(left_panel)
        
        # SAĞ PANEL - Grafikler
        right_panel = tk.Frame(main_container, width=800)
        main_container.add(right_panel)
        
        # === SOL PANEL İÇERİĞİ ===
        # Başlık
        title_label = tk.Label(left_panel, text="BIST 100 Dashboard", 
                               font=("Arial", 16, "bold"), pady=10)
        title_label.pack()
        
        # MongoDB Bağlantı Frame
        mongo_frame = ttk.LabelFrame(left_panel, text="MongoDB Bağlantısı", padding=10)
        mongo_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(mongo_frame, text="Connection String:").grid(row=0, column=0, sticky="w", pady=2)
        self.mongo_url = tk.Entry(mongo_frame, width=40)
        self.mongo_url.insert(0, "mongodb://localhost:27017/")
        self.mongo_url.grid(row=0, column=1, pady=2, padx=5)
        
        tk.Label(mongo_frame, text="Veritabanı Adı:").grid(row=1, column=0, sticky="w", pady=2)
        self.db_name = tk.Entry(mongo_frame, width=40)
        self.db_name.insert(0, "bist100_data")
        self.db_name.grid(row=1, column=1, pady=2, padx=5)
        
        tk.Label(mongo_frame, text="Koleksiyon Adı:").grid(row=2, column=0, sticky="w", pady=2)
        self.collection_name = tk.Entry(mongo_frame, width=40)
        self.collection_name.insert(0, "daily_prices")
        self.collection_name.grid(row=2, column=1, pady=2, padx=5)
        
        self.connect_btn = tk.Button(mongo_frame, text="Bağlan", command=self.connect_mongodb, 
                                     bg="#4CAF50", fg="white", width=15)
        self.connect_btn.grid(row=3, column=1, pady=5, sticky="e")
        
        # Hisse Seçimi Frame
        stock_frame = ttk.LabelFrame(left_panel, text="Hisse Seçimi ve Tarih Aralığı", padding=10)
        stock_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Sol taraf - Hisse listesi
        left_stock_frame = tk.Frame(stock_frame)
        left_stock_frame.pack(side="left", fill="both", expand=True, padx=5)
        
        tk.Label(left_stock_frame, text="BIST 100 Hisseleri:").pack(anchor="w")
        
        # Arama kutusu
        search_frame = tk.Frame(left_stock_frame)
        search_frame.pack(fill="x", pady=5)
        tk.Label(search_frame, text="Ara:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_stocks)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=15)
        search_entry.pack(side="left", padx=5)
        
        # Listbox ve Scrollbar
        listbox_frame = tk.Frame(left_stock_frame)
        listbox_frame.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(listbox_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.stock_listbox = tk.Listbox(listbox_frame, selectmode="multiple", 
                                        yscrollcommand=scrollbar.set, height=10)
        self.stock_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.stock_listbox.yview)
        
        for stock in sorted(self.bist100_stocks):
            self.stock_listbox.insert("end", stock)
        
        # Butonlar
        btn_frame = tk.Frame(left_stock_frame)
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="Tümünü Seç", command=self.select_all).pack(side="left", padx=2)
        tk.Button(btn_frame, text="Seçimi Temizle", command=self.clear_selection).pack(side="left", padx=2)
        
        # Sağ taraf - Tarih seçimi
        right_stock_frame = tk.Frame(stock_frame)
        right_stock_frame.pack(side="right", fill="y", padx=5)
        
        tk.Label(right_stock_frame, text="Tarih Aralığı:", font=("Arial", 10, "bold")).pack(anchor="w", pady=5)
        
        tk.Label(right_stock_frame, text="Başlangıç Tarihi:").pack(anchor="w")
        default_start = datetime.now() - timedelta(days=365)
        self.start_date_entry = DateEntry(right_stock_frame, width=18, background='darkblue',
                                          foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.start_date_entry.set_date(default_start)
        self.start_date_entry.pack(pady=2)
        
        tk.Label(right_stock_frame, text="Bitiş Tarihi:").pack(anchor="w", pady=(10,0))
        self.end_date_entry = DateEntry(right_stock_frame, width=18, background='darkblue',
                                        foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.end_date_entry.set_date(datetime.now())
        self.end_date_entry.pack(pady=2)
        
        tk.Label(right_stock_frame, text="Manuel Hisse Ekle:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(20,5))
        tk.Label(right_stock_frame, text="Hisse Kodu:").pack(anchor="w")
        self.manual_stock = tk.Entry(right_stock_frame, width=20)
        self.manual_stock.pack(pady=2)
        tk.Button(right_stock_frame, text="Listeye Ekle", command=self.add_manual_stock).pack(pady=5)
        
        # İşlem Butonları
        action_frame = tk.Frame(left_panel)
        action_frame.pack(fill="x", padx=10, pady=10)
        
        self.download_btn = tk.Button(action_frame, text="VERİLERİ ÇEK VE KAYDET", 
                                     command=self.start_download, bg="#2196F3", 
                                     fg="white", font=("Arial", 11, "bold"), 
                                     height=2, state="disabled")
        self.download_btn.pack(fill="x", pady=2)
        
        self.show_graph_btn = tk.Button(action_frame, text="GRAFİK GÖSTER", 
                                        command=self.show_graphs, bg="#FF9800", 
                                        fg="white", font=("Arial", 11, "bold"), 
                                        height=2, state="disabled")
        self.show_graph_btn.pack(fill="x", pady=2)
        
        self.clear_db_btn = tk.Button(action_frame, text="VERİTABANINI TEMİZLE", 
                                      command=self.clear_database, bg="#F44336", 
                                      fg="white", font=("Arial", 11, "bold"), 
                                      height=2, state="disabled")
        self.clear_db_btn.pack(fill="x", pady=2)
        
        # Progress Frame
        progress_frame = ttk.LabelFrame(left_panel, text="İşlem Durumu", padding=10)
        progress_frame.pack(fill="x", padx=10, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                             maximum=100)
        self.progress_bar.pack(fill="x", pady=5)
        
        self.status_label = tk.Label(progress_frame, text="Bağlantı bekleniyor...", fg="gray")
        self.status_label.pack()
        
        # Log Frame
        log_frame = ttk.LabelFrame(left_panel, text="İşlem Logları", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        
        # === SAĞ PANEL İÇERİĞİ - GRAFİKLER ===
        graph_title = tk.Label(right_panel, text="Grafik Görüntüleme", 
                              font=("Arial", 14, "bold"), pady=10)
        graph_title.pack()
        
        # Grafik kontrolleri
        graph_control = tk.Frame(right_panel)
        graph_control.pack(fill="x", padx=10, pady=5)
        
        tk.Label(graph_control, text="Grafik Tipi:").pack(side="left", padx=5)
        self.graph_type = ttk.Combobox(graph_control, values=["Fiyat Grafiği", "Hacim Grafiği", "Her İkisi"], 
                                       state="readonly", width=15)
        self.graph_type.set("Fiyat Grafiği")
        self.graph_type.pack(side="left", padx=5)
        
        # Grafik alanı
        self.graph_frame = tk.Frame(right_panel, bg="white")
        self.graph_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Başlangıç mesajı
        welcome_label = tk.Label(self.graph_frame, text="Grafik görüntülemek için:\n\n1. MongoDB'ye bağlanın\n2. Hisse seçin\n3. 'GRAFİK GÖSTER' butonuna tıklayın", 
                                font=("Arial", 12), bg="white", fg="gray")
        welcome_label.place(relx=0.5, rely=0.5, anchor="center")
        
    def filter_stocks(self, *args):
        search_term = self.search_var.get().upper()
        self.stock_listbox.delete(0, "end")
        for stock in sorted(self.bist100_stocks):
            if search_term in stock:
                self.stock_listbox.insert("end", stock)
    
    def select_all(self):
        self.stock_listbox.select_set(0, "end")
    
    def clear_selection(self):
        self.stock_listbox.select_clear(0, "end")
    
    def add_manual_stock(self):
        stock = self.manual_stock.get().strip().upper()
        if stock and stock not in self.bist100_stocks:
            self.bist100_stocks.append(stock)
            self.stock_listbox.delete(0, "end")
            for s in sorted(self.bist100_stocks):
                 self.stock_listbox.insert("end", s)
            self.log(f"✓ {stock} listeye eklendi")
            self.manual_stock.delete(0, "end")
        elif stock in self.bist100_stocks:
            messagebox.showinfo("Bilgi", f"{stock} zaten listede mevcut")
    
    def connect_mongodb(self):
        try:
            url = self.mongo_url.get()
            db_name = self.db_name.get()
            coll_name = self.collection_name.get()
            
            self.mongo_client = MongoClient(url, serverSelectionTimeoutMS=5000)
            self.mongo_client.admin.command('ping')
            
            self.db = self.mongo_client[db_name]
            self.collection = self.db[coll_name]
            
            self.collection.create_index([("symbol", 1), ("date", 1)], unique=True)
            
            self.status_label.config(text="✓ MongoDB'ye bağlı", fg="green")
            self.download_btn.config(state="normal")
            self.show_graph_btn.config(state="normal")
            self.clear_db_btn.config(state="normal")
            self.log(f"✓ MongoDB bağlantısı başarılı: {db_name}.{coll_name}")
            
        except Exception as e:
            self.status_label.config(text="✗ Bağlantı hatası", fg="red")
            self.log(f"✗ Bağlantı hatası: {str(e)}")
            messagebox.showerror("Hata", f"MongoDB bağlantı hatası:\n{str(e)}")
    
    def log(self, message):
        def _insert_log():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.insert("end", f"[{timestamp}] {message}\n")
            self.log_text.see("end")
        
        self.root.after(0, _insert_log)
    
    def start_download(self):
        selected_indices = self.stock_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Uyarı", "Lütfen en az bir hisse seçin!")
            return
        
        if self.collection is None:
            messagebox.showerror("Hata", "Lütfen önce MongoDB'ye bağlanın!")
            return
        
        selected_stocks = [self.stock_listbox.get(i) for i in selected_indices]
        start_date = self.start_date_entry.get_date().strftime("%Y-%m-%d")
        end_date = self.end_date_entry.get_date().strftime("%Y-%m-%d")
        
        self.download_btn.config(state="disabled")
        thread = threading.Thread(target=self.download_data, 
                                 args=(selected_stocks, start_date, end_date))
        thread.daemon = True
        thread.start()
    
    def download_data(self, stocks, start_date, end_date):
        total = len(stocks)
        success_count = 0
        error_count = 0
        total_upserts = 0
        
        self.log(f"*** {total} hisse için veri çekme başladı ***")
        self.log(f"→ Tarih aralığı: {start_date} - {end_date}")
        
        for i, symbol in enumerate(stocks):
            try:
                ticker = f"{symbol}.IS"
                self.log(f"→ ({i+1}/{total}) {symbol} indiriliyor...")
                
                data = yf.download(ticker, start=start_date, end=end_date, progress=False)
                if data.empty:
                    self.log(f"⚠️ {symbol}: .IS uzantısı için veri yok, alternatif deneniyor...")
                    data = yf.download(symbol, start=start_date, end=end_date, progress=False)
                
                if data.empty:
                    self.log(f"✗ {symbol}: Veri bulunamadı!")
                    error_count += 1
                else:
                    self.log(f"  → Çekilen günlük kayıt sayısı: {len(data)}")
                    
                    operations = []
                    
                    for date, row in data.iterrows():
                        timestamp_dt = date.to_pydatetime()
                        date_str = timestamp_dt.strftime("%Y-%m-%d")

                        record = {
                            "symbol": symbol,
                            "date": date_str,
                            "timestamp": timestamp_dt, 
                            "open": float(row['Open']) if 'Open' in row else None,
                            "high": float(row['High']) if 'High' in row else None,
                            "low": float(row['Low']) if 'Low' in row else None,
                            "close": float(row['Close']) if 'Close' in row else None,
                            "volume": int(row['Volume']) if 'Volume' in row else 0,
                            "adj_close": float(row['Adj Close']) if 'Adj Close' in row else None
                        }
                        
                        update_op = UpdateOne(
                            filter={"symbol": symbol, "date": date_str}, 
                            update={"$set": record}, 
                            upsert=True
                        )
                        operations.append(update_op)
                    
                    if operations:
                        try:
                            result = self.collection.bulk_write(operations, ordered=False)
                            inserted = result.upserted_count
                            updated = result.modified_count
                            
                            self.log(f"✓ {symbol}: {inserted} yeni, {updated} güncellendi.")
                            success_count += 1
                            total_upserts += (inserted + updated)
                            
                        except Exception as e:
                            self.log(f"✗ {symbol} MongoDB hatası: {str(e)}")
                            error_count += 1
                    
            except Exception as e:
                self.log(f"✗ {symbol} hatası: {str(e)}")
                error_count += 1
            
            progress = ((i + 1) / total) * 100
            status_text = f"İşleniyor: {i+1}/{total} hisse"
            self.root.after(0, self.progress_var.set, progress)
            self.root.after(0, self.status_label.config, {"text": status_text, "fg": "orange"})

        self.log(f"\n{'='*50}")
        self.log(f"✓ İşlem tamamlandı!")
        self.log(f"  Başarılı: {success_count} | Hatalı: {error_count}")
        self.log(f"  MongoDB'de İşlenen: {total_upserts}")
        self.log(f"{'='*50}\n")
        
        try:
            db_count = self.collection.count_documents({})
            self.log(f"📊 Toplam kayıt: {db_count}")
        except:
            pass
            
        self.root.after(0, self.status_label.config, {"text": "İşlem tamamlandı", "fg": "green"})
        self.root.after(0, self.download_btn.config, {"state": "normal"})
        self.root.after(0, messagebox.showinfo, "Tamamlandı", 
                        f"Başarılı: {success_count}\nHatalı: {error_count}\nKayıt: {total_upserts}")
        
        # İşlem bittiğinde otomatik grafik göster
        if success_count > 0 and len(selected_stocks) <= 5:
            self.root.after(100, lambda: self.show_graphs(auto_show=True))
        elif success_count > 0 and len(selected_stocks) > 5:
            self.log("ℹ️ Otomatik grafik için 5'ten az hisse seçin")
    
    def show_graphs(self, auto_show=False):
        selected_indices = self.stock_listbox.curselection()
        if not selected_indices:
            if not auto_show:
                messagebox.showwarning("Uyarı", "Lütfen görüntülemek için hisse seçin!")
            return
        
        if self.collection is None:
            messagebox.showerror("Hata", "MongoDB bağlantısı yok!")
            return
        
        # Maksimum 5 hisse için grafik göster
        if len(selected_indices) > 5:
            if not auto_show:
                messagebox.showwarning("Uyarı", "Görsellik için maksimum 5 hisse seçin!")
            return
        
        selected_stocks = [self.stock_listbox.get(i) for i in selected_indices]
        start_date = self.start_date_entry.get_date().strftime("%Y-%m-%d")
        end_date = self.end_date_entry.get_date().strftime("%Y-%m-%d")
        
        self.log(f"📊 {len(selected_stocks)} hisse için grafik hazırlanıyor...")
        
        # Mevcut grafikleri temizle
        for widget in self.graph_frame.winfo_children():
            widget.destroy()
        
        # Verileri MongoDB'den çek
        stock_data = {}
        for symbol in selected_stocks:
            try:
                cursor = self.collection.find({
                    "symbol": symbol,
                    "date": {"$gte": start_date, "$lte": end_date}
                }).sort("date", 1)
                
                records = list(cursor)
                if records:
                    df = pd.DataFrame(records)
                    df['date'] = pd.to_datetime(df['date'])
                    stock_data[symbol] = df
                    self.log(f"  ✓ {symbol}: {len(df)} kayıt bulundu")
                else:
                    self.log(f"  ⚠️ {symbol}: Veri bulunamadı")
            except Exception as e:
                self.log(f"  ✗ {symbol}: Hata - {str(e)}")
        
        if not stock_data:
            if not auto_show:
                messagebox.showinfo("Bilgi", "Seçilen hisseler için grafik verisi bulunamadı!")
            return
        
        # Grafik tipine göre çiz
        graph_type = self.graph_type.get()
        
        if graph_type == "Her İkisi":
            fig = Figure(figsize=(10, 8))
            ax1 = fig.add_subplot(211)
            ax2 = fig.add_subplot(212)
        else:
            fig = Figure(figsize=(10, 6))
            ax1 = fig.add_subplot(111)
            ax2 = None
        
        # Fiyat grafiği
        if graph_type in ["Fiyat Grafiği", "Her İkisi"]:
            for symbol, df in stock_data.items():
                ax1.plot(df['date'], df['close'], label=symbol, linewidth=2, marker='o', markersize=3)
            
            ax1.set_title('Kapanış Fiyatları', fontsize=14, fontweight='bold')
            ax1.set_xlabel('Tarih', fontsize=11)
            ax1.set_ylabel('Fiyat (TL)', fontsize=11)
            ax1.legend(loc='best', fontsize=10)
            ax1.grid(True, alpha=0.3)
            ax1.tick_params(axis='x', rotation=45)
        
        # Hacim grafiği
        if graph_type in ["Hacim Grafiği", "Her İkisi"]:
            target_ax = ax2 if ax2 else ax1
            
            for symbol, df in stock_data.items():
                target_ax.bar(df['date'], df['volume'], label=symbol, alpha=0.7, width=2)
            
            target_ax.set_title('İşlem Hacmi', fontsize=14, fontweight='bold')
            target_ax.set_xlabel('Tarih', fontsize=11)
            target_ax.set_ylabel('Hacim', fontsize=11)
            target_ax.legend(loc='best', fontsize=10)
            target_ax.grid(True, alpha=0.3, axis='y')
            target_ax.tick_params(axis='x', rotation=45)
        
        fig.tight_layout()
        
        # Tkinter canvas'a ekle
        canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        
        self.log(f"✓ Grafik başarıyla oluşturuldu!")
    
    def clear_database(self):
        """MongoDB koleksiyonundaki tüm verileri siler"""
        if self.collection is None:
            messagebox.showerror("Hata", "MongoDB bağlantısı yok!")
            return
        
        # Onay dialogu
        result = messagebox.askyesno(
            "Onay", 
            "Veritabanındaki TÜM verileri silmek istediğinize emin misiniz?\n\nBu işlem geri alınamaz!",
            icon='warning'
        )
        
        if not result:
            self.log("ℹ️ Veritabanı temizleme işlemi iptal edildi")
            return
        
        try:
            # Kayıt sayısını al
            count_before = self.collection.count_documents({})
            
            # Tüm kayıtları sil
            delete_result = self.collection.delete_many({})
            deleted_count = delete_result.deleted_count
            
            self.log(f"🗑️ Veritabanı temizlendi!")
            self.log(f"  Silinen kayıt sayısı: {deleted_count}")
            
            # Grafik alanını temizle
            for widget in self.graph_frame.winfo_children():
                widget.destroy()
            
            welcome_label = tk.Label(
                self.graph_frame, 
                text="Veritabanı temizlendi.\n\nYeni veri çekmek için:\n1. Hisse seçin\n2. 'VERİLERİ ÇEK VE KAYDET' butonuna tıklayın", 
                font=("Arial", 12), 
                bg="white", 
                fg="gray"
            )
            welcome_label.place(relx=0.5, rely=0.5, anchor="center")
            
            messagebox.showinfo("Başarılı", f"Veritabanı temizlendi!\n\nSilinen kayıt: {deleted_count}")
            
        except Exception as e:
            self.log(f"✗ Veritabanı temizleme hatası: {str(e)}")
            messagebox.showerror("Hata", f"Veritabanı temizlenirken hata oluştu:\n{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = BIST100Dashboard(root)
    root.mainloop()