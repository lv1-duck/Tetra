from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image as KivyImage
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from PIL import Image
import io
import os
from threading import Thread

try:
    from pdf2image import convert_from_path
    import PyPDF2
    PDF_LIBRARIES_AVAILABLE = True
except ImportError:
    PDF_LIBRARIES_AVAILABLE = False


class ViewerScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        
        # Initialize PDF state
        self.current_pdf_path = None
        self.current_page = 1
        self.total_pages = 0
        self.page_cache = {}  # Simple cache for rendered pages
        self.max_cache_size = 3  # Keep only 3 pages in memory for mobile
        
        # Create UI elements
        self.setup_ui()
        
        # Check if libraries are available
        if not PDF_LIBRARIES_AVAILABLE:
            self.show_error("PDF libraries not available. Install: pip install pdf2image PyPDF2")
    
    def setup_ui(self):
        """Create the viewer interface"""
        # Top navigation bar
        nav_layout = BoxLayout(orientation='horizontal', size_hint_y=0.1)
        
        self.prev_btn = Button(text='◀ Previous', size_hint_x=0.3)
        self.prev_btn.bind(on_press=lambda x: self.show_previous())
        
        self.page_label = Label(text='No PDF loaded', size_hint_x=0.4)
        
        self.next_btn = Button(text='Next ▶', size_hint_x=0.3)
        self.next_btn.bind(on_press=lambda x: self.show_next())
        
        nav_layout.add_widget(self.prev_btn)
        nav_layout.add_widget(self.page_label)
        nav_layout.add_widget(self.next_btn)
        
        # PDF display area
        self.pdf_image = KivyImage(size_hint_y=0.9)
        
        # Add to main layout
        self.add_widget(nav_layout)
        self.add_widget(self.pdf_image)
        
        # Initially disable navigation
        self.update_navigation_state()
    
    def load_pdf(self, path):
        """Load PDF and render first page"""
        if not PDF_LIBRARIES_AVAILABLE:
            self.show_error("PDF libraries not available")
            return
        
        if not os.path.exists(path):
            self.show_error("PDF file not found")
            return
        
        try:
            # Get total pages using PyPDF2 (lightweight)
            with open(path, 'rb') as f:
                reader = PyPDF2.PdfReader(f, strict=False)
                total_pages = len(reader.pages)
            
            # Store PDF info
            self.current_pdf_path = path
            self.total_pages = total_pages
            self.current_page = 1
            self.page_cache.clear()  # Clear any existing cache
            
            # Update UI
            self.update_page_label()
            self.update_navigation_state()
            
            # Render first page in background thread
            self.render_page_async(1)
            
        except Exception as e:
            self.show_error(f"Failed to load PDF: {str(e)[:50]}")
    
    def show_next(self):
        """Navigate to next page"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_page_label()
            self.update_navigation_state()
            self.render_page_async(self.current_page)
    
    def show_previous(self):
        """Navigate to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.update_page_label()
            self.update_navigation_state()
            self.render_page_async(self.current_page)
    
    def render_page_async(self, page_number):
        """Render page in background thread to avoid UI blocking"""
        # Check cache first
        if page_number in self.page_cache:
            Clock.schedule_once(lambda dt: self.display_cached_page(page_number))
            return
        
        # Show loading state
        Clock.schedule_once(lambda dt: self.show_loading())
        
        # Render in background
        thread = Thread(target=self._render_page_thread, args=(page_number,))
        thread.daemon = True
        thread.start()
    
    def _render_page_thread(self, page_number):
        """Background thread for page rendering"""
        try:
            # Convert PDF page to image
            images = convert_from_path(
                self.current_pdf_path,
                first_page=page_number,
                last_page=page_number,
                dpi=150  # Good balance for mobile
            )
            
            if images:
                pil_image = images[0]
                
                # Optimize for mobile display
                # Resize if too large (save memory)
                max_width = 800  # Adjust based on your needs
                if pil_image.width > max_width:
                    ratio = max_width / pil_image.width
                    new_height = int(pil_image.height * ratio)
                    pil_image = pil_image.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert to bytes for Kivy
                img_bytes = io.BytesIO()
                pil_image.save(img_bytes, format='PNG', optimize=True)
                img_bytes.seek(0)
                
                # Cache the image data
                self.add_to_cache(page_number, img_bytes.getvalue())
                
                # Schedule UI update on main thread
                Clock.schedule_once(lambda dt: self.display_page_image(img_bytes.getvalue()))
            else:
                Clock.schedule_once(lambda dt: self.show_error("Failed to render page"))
                
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_error(f"Render error: {str(e)[:30]}"))
    
    def display_page_image(self, image_data):
        """Display the rendered page image"""
        try:
            # Create Kivy image from bytes
            core_image = CoreImage(io.BytesIO(image_data), ext='png')
            self.pdf_image.texture = core_image.texture
        except Exception as e:
            self.show_error(f"Display error: {str(e)[:30]}")
    
    def display_cached_page(self, page_number):
        """Display page from cache"""
        if page_number in self.page_cache:
            self.display_page_image(self.page_cache[page_number])
    
    def add_to_cache(self, page_number, image_data):
        """Add page to cache with size limit"""
        # Remove oldest if cache is full
        if len(self.page_cache) >= self.max_cache_size:
            # Remove the page furthest from current page
            pages_to_remove = []
            for cached_page in self.page_cache.keys():
                if abs(cached_page - self.current_page) > 1:
                    pages_to_remove.append(cached_page)
            
            # Remove at least one page
            if pages_to_remove:
                self.page_cache.pop(pages_to_remove[0])
            elif self.page_cache:
                # Remove any page if none are far
                self.page_cache.pop(next(iter(self.page_cache)))
        
        self.page_cache[page_number] = image_data
    
    def show_loading(self):
        """Show loading indicator"""
        self.page_label.text = f"Loading page {self.current_page}..."
    
    def show_error(self, message):
        """Display error message"""
        self.page_label.text = f"Error: {message}"
        # Clear the image
        self.pdf_image.texture = None
    
    def update_page_label(self):
        """Update page counter display"""
        if self.total_pages > 0:
            self.page_label.text = f"Page {self.current_page} of {self.total_pages}"
        else:
            self.page_label.text = "No PDF loaded"
    
    def update_navigation_state(self):
        """Enable/disable navigation buttons based on current page"""
        if self.total_pages == 0:
            self.prev_btn.disabled = True
            self.next_btn.disabled = True
        else:
            self.prev_btn.disabled = (self.current_page <= 1)
            self.next_btn.disabled = (self.current_page >= self.total_pages)
    
    def jump_to_page(self, page_number):
        """Jump directly to a specific page"""
        if 1 <= page_number <= self.total_pages:
            self.current_page = page_number
            self.update_page_label()
            self.update_navigation_state()
            self.render_page_async(page_number)
    
    def preload_adjacent_pages(self):
        """Preload next/previous pages for smoother navigation"""
        if not self.current_pdf_path:
            return
        
        # Preload next page
        if self.current_page < self.total_pages:
            next_page = self.current_page + 1
            if next_page not in self.page_cache:
                thread = Thread(target=self._render_page_thread, args=(next_page,))
                thread.daemon = True
                thread.start()
        
        # Preload previous page
        if self.current_page > 1:
            prev_page = self.current_page - 1
            if prev_page not in self.page_cache:
                thread = Thread(target=self._render_page_thread, args=(prev_page,))
                thread.daemon = True
                thread.start()
    
    def get_pdf_info(self):
        """Get basic PDF information"""
        if not self.current_pdf_path:
            return None
        
        return {
            'path': self.current_pdf_path,
            'filename': os.path.basename(self.current_pdf_path),
            'current_page': self.current_page,
            'total_pages': self.total_pages,
            'cached_pages': list(self.page_cache.keys())
        }


