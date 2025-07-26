"""Desktop viewer screen class file"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image as KivyImage
from kivy.core.image import Image as CoreImage
from kivy.uix.scatter import Scatter
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from kivy.core.window import Window
from PIL import Image
import io
import os
from threading import Thread

try:
    import fitz  # PyMuPDF
    PDF_LIBRARIES_AVAILABLE = True
except ImportError:
    PDF_LIBRARIES_AVAILABLE = False


class ZoomableScrollableImage(ScrollView):
    """Desktop zoomable and scrollable image widget"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_scroll_x = True
        self.do_scroll_y = True
        self.bar_width = 10
        self.scroll_type = ['bars']
        
        # Create scatter for zooming
        self.scatter = Scatter(
            do_rotation=False,
            scale_min=0.5,
            scale_max=5.0,
            size_hint=(None, None)
        )
        
        # Create image
        self.image = KivyImage(
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(None, None)
        )
        
        self.scatter.add_widget(self.image)
        self.add_widget(self.scatter)
        
        # Bind events
        self.scatter.bind(scale=self.on_scale_change)
        self.image.bind(texture=self.on_texture_change)
        
    def on_texture_change(self, instance, texture):
        """Update image size when texture changes"""
        if texture:
            # Set image size to texture size
            self.image.size = texture.size
            # Update scatter size to match image
            self.scatter.size = texture.size
            # Center the image
            self.center_image()
    
    def on_scale_change(self, instance, scale):
        """Update scroll view when scale changes"""
        if self.image.texture:
            # Update scatter size based on scale
            texture_size = self.image.texture.size
            self.scatter.size = (texture_size[0] * scale, texture_size[1] * scale)
    
    def center_image(self):
        """Center the image in the scroll view"""
        if self.image.texture:
            # Reset scatter position and scale
            self.scatter.scale = 1.0
            self.scatter.pos = (0, 0)
            # Center scroll position
            Clock.schedule_once(self._center_scroll, 0.1)
    
    def _center_scroll(self, dt):
        """Center the scroll position"""
        self.scroll_x = 0.5
        self.scroll_y = 0.5
    
    def zoom_in(self):
        """Zoom in by 25%"""
        new_scale = min(self.scatter.scale * 1.25, self.scatter.scale_max)
        self.scatter.scale = new_scale
    
    def zoom_out(self):
        """Zoom out by 25%"""
        new_scale = max(self.scatter.scale * 0.8, self.scatter.scale_min)
        self.scatter.scale = new_scale
    
    def fit_to_screen(self):
        """Fit image to screen"""
        self.scatter.scale = 1.0
        self.center_image()


class ViewerScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        
        # Initialize PDF state
        self.current_pdf_path = None
        self.pdf_document = None
        self.current_page = 1
        self.total_pages = 0
        self.page_cache = {}
        
        # Desktop-optimized settings
        self.max_cache_size = 5  # More memory available on desktop
        self.zoom_factor = 2.0   # Higher quality for desktop displays
        self.max_width = None    # Don't limit width - let it scale to fit screen
        self.target_dpi = 150    # Target DPI for good quality
        
        # Create UI elements
        self.setup_ui()
        
        # Bind keyboard events for desktop
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_dropfile=self.on_file_drop)
        
        # Check if libraries are available
        if not PDF_LIBRARIES_AVAILABLE:
            self.show_error("PDF libraries not available. Install: pip install PyMuPDF")
    
    def setup_ui(self):
        # DESKTOP NAVIGATION BAR with zoom controls
        nav_layout = BoxLayout(orientation='horizontal', size_hint_y=0.08)

        # Navigation buttons
        back_btn = Button(text='← Back', size_hint_x=0.15, font_size='14sp')
        back_btn.bind(on_press=lambda x: self.go_back())
        
        self.prev_btn = Button(text='◀ Previous', size_hint_x=0.15, font_size='14sp')
        self.prev_btn.bind(on_press=lambda x: self.show_previous())
        
        self.page_label = Label(text='No PDF loaded', size_hint_x=0.2, font_size='14sp')
        
        self.next_btn = Button(text='Next ▶', size_hint_x=0.15, font_size='14sp')
        self.next_btn.bind(on_press=lambda x: self.show_next())
        
        # Zoom controls
        zoom_out_btn = Button(text='−', size_hint_x=0.08, font_size='16sp')
        zoom_out_btn.bind(on_press=lambda x: self.zoom_out())
        
        fit_btn = Button(text='Fit', size_hint_x=0.09, font_size='12sp')
        fit_btn.bind(on_press=lambda x: self.fit_to_screen())
        
        zoom_in_btn = Button(text='+', size_hint_x=0.08, font_size='16sp')
        zoom_in_btn.bind(on_press=lambda x: self.zoom_in())
        
        self.zoom_label = Label(text='100%', size_hint_x=0.1, font_size='12sp')

        nav_layout.add_widget(back_btn)
        nav_layout.add_widget(self.prev_btn)
        nav_layout.add_widget(self.page_label)
        nav_layout.add_widget(self.next_btn)
        nav_layout.add_widget(zoom_out_btn)
        nav_layout.add_widget(fit_btn)
        nav_layout.add_widget(zoom_in_btn)
        nav_layout.add_widget(self.zoom_label)
        
        # ZOOMABLE PDF DISPLAY AREA
        self.pdf_viewer = ZoomableScrollableImage(size_hint_y=0.92)
        self.pdf_viewer.scatter.bind(scale=self.on_zoom_change)
        
        # Add to main layout
        self.add_widget(nav_layout)
        self.add_widget(self.pdf_viewer)
        
        # Initially disable navigation
        self.update_navigation_state()

    def go_back(self):
        """Return to main screen"""
        from kivy.app import App
        app = App.get_running_app()
        app.root.current = 'main'
        
    def load_pdf(self, path):
        """Load PDF and render first page"""
        if not PDF_LIBRARIES_AVAILABLE:
            self.show_error("PDF libraries not available")
            return
        
        if not os.path.exists(path):
            self.show_error("PDF file not found")
            return
        
        try:
            # Close existing document if any
            if self.pdf_document:
                self.pdf_document.close()
            
            # Open PDF document with PyMuPDF
            self.pdf_document = fitz.open(path)
            
            # Check if document is valid and get total pages
            if self.pdf_document.is_pdf:
                total_pages = len(self.pdf_document)
            else:
                self.show_error("Invalid PDF file")
                return
            
            # Store PDF info
            self.current_pdf_path = path
            self.total_pages = total_pages
            self.current_page = 1
            self.page_cache.clear()
            
            # Update UI
            self.update_page_label()
            self.update_navigation_state()
            
            # Render first page in background thread
            self.render_page_async(1)
            
            # Preload adjacent pages for smooth navigation
            Clock.schedule_once(lambda dt: self.preload_adjacent_pages(), 1.0)
            
        except Exception as e:
            self.show_error(f"Failed to load PDF: {str(e)[:50]}")
    
    def show_next(self):
        """Navigate to next page"""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_page_label()
            self.update_navigation_state()
            self.render_page_async(self.current_page)
            # Preload next pages
            Clock.schedule_once(lambda dt: self.preload_adjacent_pages(), 0.5)
    
    def show_previous(self):
        """Navigate to previous page"""
        if self.current_page > 1:
            self.current_page -= 1
            self.update_page_label()
            self.update_navigation_state()
            self.render_page_async(self.current_page)
            # Preload adjacent pages
            Clock.schedule_once(lambda dt: self.preload_adjacent_pages(), 0.5)
    
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
        """Background thread for page rendering using PyMuPDF"""
        try:
            if not self.pdf_document:
                Clock.schedule_once(lambda dt: self.show_error("No PDF loaded"))
                return
            
            # Get the page (PyMuPDF uses 0-based indexing)
            page = self.pdf_document[page_number - 1]
            
            # Calculate optimal zoom to fit screen width
            page_rect = page.rect
            # Use screen-adaptive zoom instead of fixed zoom
            mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            
            # Render page to pixmap with high quality
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            # Convert pixmap to PIL Image
            img_data = pix.tobytes("png")
            pil_image = Image.open(io.BytesIO(img_data))
            
            # For desktop, we want to maintain aspect ratio and fit to available space
            # The KivyImage with keep_ratio=True will handle the final scaling
            
            # Convert to PNG for best quality on desktop
            img_bytes = io.BytesIO()
            pil_image.save(img_bytes, format='PNG', optimize=True)
            img_bytes.seek(0)
            
            # Cache the image data
            self.add_to_cache(page_number, img_bytes.getvalue())
            
            # Schedule UI update on main thread
            Clock.schedule_once(lambda dt: self.display_page_image(img_bytes.getvalue()))
            
            # Clean up PyMuPDF pixmap
            pix = None
                
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_error(f"Render error: {str(e)[:30]}"))
    
    def display_page_image(self, image_data):
        """Display the rendered page image"""
        try:
            # Create Kivy image from bytes
            core_image = CoreImage(io.BytesIO(image_data), ext='png')
            self.pdf_viewer.image.texture = core_image.texture
        except Exception as e:
            self.show_error(f"Display error: {str(e)[:30]}")
    
    def display_cached_page(self, page_number):
        """Display page from cache"""
        if page_number in self.page_cache:
            self.display_page_image(self.page_cache[page_number])
    
    # Zoom control methods
    def zoom_in(self):
        """Zoom in"""
        self.pdf_viewer.zoom_in()
    
    def zoom_out(self):
        """Zoom out"""
        self.pdf_viewer.zoom_out()
    
    def fit_to_screen(self):
        """Fit to screen"""
        self.pdf_viewer.fit_to_screen()
    
    def on_zoom_change(self, instance, scale):
        """Update zoom label when scale changes"""
        zoom_percent = int(scale * 100)
        self.zoom_label.text = f'{zoom_percent}%'
    
    def on_key_down(self, window, key, scancode, codepoint, modifier):
        """Handle keyboard shortcuts"""
        if not self.pdf_document:
            return False
            
        # Page navigation with arrow keys
        if key == 276:  # Left arrow
            self.show_previous()
            return True
        elif key == 275:  # Right arrow
            self.show_next()
            return True
        # Zoom with +/- keys
        elif key == 61 or key == 270:  # + or numpad +
            self.zoom_in()
            return True
        elif key == 45 or key == 269:  # - or numpad -
            self.zoom_out()
            return True
        # Fit to screen with F key
        elif key == 102:  # F key
            self.fit_to_screen()
            return True
        # Home/End for first/last page
        elif key == 278:  # Home
            self.jump_to_page(1)
            return True
        elif key == 279:  # End
            self.jump_to_page(self.total_pages)
            return True
        
        return False
    
    def on_file_drop(self, window, file_path):
        """Handle drag and drop files"""
        if file_path.decode('utf-8').lower().endswith('.pdf'):
            self.load_pdf(file_path.decode('utf-8'))
            return True
        return False
    
    def add_to_cache(self, page_number, image_data):
        """Add page to cache with desktop-appropriate size limit"""
        # Desktop has more memory, so more generous cache management
        if len(self.page_cache) >= self.max_cache_size:
            # Remove pages furthest from current page
            pages_to_remove = []
            for cached_page in self.page_cache.keys():
                if abs(cached_page - self.current_page) > 2:  # Keep 2 pages around current
                    pages_to_remove.append(cached_page)
            
            # Remove the furthest page
            if pages_to_remove:
                furthest_page = max(pages_to_remove, key=lambda p: abs(p - self.current_page))
                self.page_cache.pop(furthest_page)
            elif self.page_cache:
                # Remove oldest entry if all are close
                self.page_cache.pop(next(iter(self.page_cache)))
        
        self.page_cache[page_number] = image_data
    
    def show_loading(self):
        """Show loading indicator"""
        self.page_label.text = f"Loading page {self.current_page}..."
    
    def show_error(self, message):
        """Display error message"""
        self.page_label.text = f"Error: {message}"
        # Clear the image
        self.pdf_viewer.image.texture = None
    
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
            Clock.schedule_once(lambda dt: self.preload_adjacent_pages(), 0.5)
    
    def preload_adjacent_pages(self):
        """Preload next/previous pages for smoother navigation"""
        if not self.current_pdf_path or not self.pdf_document:
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
    
    def __del__(self):
        """Clean up resources when object is destroyed"""
        if self.pdf_document:
            self.pdf_document.close()