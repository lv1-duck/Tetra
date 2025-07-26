"""Mobile-optimized viewer screen class file"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import Image as KivyImage
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock
from kivy.uix.scatter import Scatter
from kivy.uix.widget import Widget
from PIL import Image
import io
import os
from threading import Thread
import gc

try:
    import fitz  # PyMuPDF
    PDF_LIBRARIES_AVAILABLE = True
except ImportError:
    PDF_LIBRARIES_AVAILABLE = False


class ZoomableImage(Scatter):
    """Touch-enabled zoomable image widget for mobile"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_rotation = False 
        self.scale_min = 0.5
        self.scale_max = 5.0
        
        self.image = KivyImage(
            allow_stretch=True,
            keep_ratio=True
        )
        self.add_widget(self.image)
        
        # Track double tap for fit-to-screen
        self.last_touch_time = 0
        self.double_tap_threshold = 0.3
    
    def on_touch_down(self, touch):
        # Store initial touch for swipe detection and double tap
        if self.collide_point(*touch.pos):
            self.initial_touch = touch.pos
            
            # Check for double tap
            current_time = touch.time_start
            if current_time - self.last_touch_time < self.double_tap_threshold:
                # Double tap - fit to screen or zoom to 2x
                if self.scale <= 1.1:
                    self.scale = 2.0  # Zoom in
                else:
                    self.scale = 1.0  # Fit to screen
                    self.pos = (0, 0)
                return True
            self.last_touch_time = current_time
            
            return super().on_touch_down(touch)
        return False
    
    def on_touch_up(self, touch):
        if hasattr(self, 'initial_touch') and self.collide_point(*touch.pos):
            # Detect swipe gestures (only when not zoomed)
            dx = touch.pos[0] - self.initial_touch[0]
            dy = touch.pos[1] - self.initial_touch[1]
            
            # Horizontal swipe for page navigation (if not zoomed much)
            if abs(dx) > 100 and abs(dy) < 50 and self.scale <= 1.2:
                if dx > 0:  # Right swipe - previous page
                    self.parent.parent.show_previous()
                else:  # Left swipe - next page  
                    self.parent.parent.show_next()
                return True
        
        return super().on_touch_up(touch)
    
    def fit_to_screen(self):
        """Reset zoom and center"""
        self.scale = 1.0
        self.pos = (0, 0)


class ViewerScreen(BoxLayout):
    def __init__(self, mobile_mode=True, **kwargs):
        # Remove mobile_mode from kwargs before passing to parent
        if 'mobile_mode' in kwargs:
            kwargs.pop('mobile_mode')
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        
        # Initialize PDF state
        self.current_pdf_path = None
        self.pdf_document = None
        self.current_page = 1
        self.total_pages = 0
        self.page_cache = {}
        
        # Mobile-optimized settings
        self.max_cache_size = 2  # Aggressive memory management for mobile
        self.zoom_factor = 1.5   # Balanced quality and performance
        self.max_width = None    # Let it scale to fit screen
        self.render_quality = 0.8  # Reduce quality for speed
        self.target_dpi = 120    # Lower DPI for mobile performance
        
        # Create UI elements
        self.setup_ui()
        
        # Check if libraries are available
        if not PDF_LIBRARIES_AVAILABLE:
            self.show_error("PDF libraries not available. Install: pip install PyMuPDF")
    
    def setup_ui(self):
        # MOBILE-OPTIMIZED NAVIGATION BAR with zoom controls
        nav_layout = BoxLayout(orientation='horizontal', size_hint_y=0.12, spacing='5dp')

        # Navigation buttons
        back_btn = Button(text='← Back', size_hint_x=0.2, font_size='16sp')
        back_btn.bind(on_press=lambda x: self.go_back())
        
        self.prev_btn = Button(text='◀', size_hint_x=0.15, font_size='18sp')
        self.prev_btn.bind(on_press=lambda x: self.show_previous())
        
        self.page_label = Label(text='No PDF loaded', size_hint_x=0.25, font_size='14sp')
        
        self.next_btn = Button(text='▶', size_hint_x=0.15, font_size='18sp')
        self.next_btn.bind(on_press=lambda x: self.show_next())
        
        # Zoom controls for mobile
        zoom_out_btn = Button(text='−', size_hint_x=0.1, font_size='18sp')
        zoom_out_btn.bind(on_press=lambda x: self.zoom_out())
        
        fit_btn = Button(text='⌂', size_hint_x=0.1, font_size='16sp')  # Home icon for fit
        fit_btn.bind(on_press=lambda x: self.fit_to_screen())
        
        zoom_in_btn = Button(text='+', size_hint_x=0.1, font_size='18sp')
        zoom_in_btn.bind(on_press=lambda x: self.zoom_in())

        nav_layout.add_widget(back_btn)
        nav_layout.add_widget(self.prev_btn)
        nav_layout.add_widget(self.page_label)
        nav_layout.add_widget(self.next_btn)
        nav_layout.add_widget(zoom_out_btn)
        nav_layout.add_widget(fit_btn)
        nav_layout.add_widget(zoom_in_btn)
        
        # ZOOMABLE PDF DISPLAY AREA - Full screen utilization
        scroll_container = Widget(size_hint_y=0.88)
        self.pdf_zoom = ZoomableImage(
            size_hint=(1, 1), 
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        # Make sure the inner image fills available space
        self.pdf_zoom.image.allow_stretch = True
        self.pdf_zoom.image.keep_ratio = True
        scroll_container.add_widget(self.pdf_zoom)
        
        # Add to main layout
        self.add_widget(nav_layout)
        self.add_widget(scroll_container)
        
        # Initially disable navigation
        self.update_navigation_state()

    def go_back(self):
        """Return to main screen"""
        # Clean up before leaving
        self.cleanup_resources()
        from kivy.app import App
        app = App.get_running_app()
        app.root.current = 'main'
        
    def load_pdf(self, path):
        """Load PDF and render first page - mobile optimized"""
        if not PDF_LIBRARIES_AVAILABLE:
            self.show_error("PDF libraries not available")
            return
        
        if not os.path.exists(path):
            self.show_error("PDF file not found")
            return
        
        try:
            # Clean up previous document
            self.cleanup_resources()
            
            # Open PDF document with PyMuPDF
            self.pdf_document = fitz.open(path)
            
            # Check if document is valid
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
            
            # Render first page
            self.render_page_async(1)
            
        except Exception as e:
            self.show_error(f"Failed to load PDF: {str(e)[:50]}")
    
    def show_next(self):
        """Navigate to next page with mobile optimizations"""
        if self.current_page < self.total_pages:
            # Reset zoom when changing pages
            self.pdf_zoom.fit_to_screen()
            
            self.current_page += 1
            self.update_page_label()
            self.update_navigation_state()
            self.render_page_async(self.current_page)
            
            # Aggressive cleanup for mobile
            self.cleanup_old_cache()
    
    def show_previous(self):
        """Navigate to previous page with mobile optimizations"""
        if self.current_page > 1:
            # Reset zoom when changing pages
            self.pdf_zoom.fit_to_screen()
            
            self.current_page -= 1
            self.update_page_label()
            self.update_navigation_state()
            self.render_page_async(self.current_page)
            
            # Aggressive cleanup for mobile
            self.cleanup_old_cache()
    
    # Zoom control methods for mobile
    def zoom_in(self):
        """Zoom in by 50% for mobile"""
        new_scale = min(self.pdf_zoom.scale * 1.5, self.pdf_zoom.scale_max)
        self.pdf_zoom.scale = new_scale
    
    def zoom_out(self):
        """Zoom out by 33% for mobile"""
        new_scale = max(self.pdf_zoom.scale * 0.67, self.pdf_zoom.scale_min)
        self.pdf_zoom.scale = new_scale
    
    def fit_to_screen(self):
        """Fit to screen for mobile"""
        self.pdf_zoom.fit_to_screen()
    
    def render_page_async(self, page_number):
        """Mobile-optimized async rendering"""
        # Check cache first
        if page_number in self.page_cache:
            Clock.schedule_once(lambda dt: self.display_cached_page(page_number))
            return
        
        # Show loading state
        Clock.schedule_once(lambda dt: self.show_loading())
        
        # Render in background with lower priority
        thread = Thread(target=self._render_page_thread, args=(page_number,))
        thread.daemon = True
        thread.start()
    
    def _render_page_thread(self, page_number):
        """Mobile-optimized background rendering"""
        try:
            if not self.pdf_document:
                Clock.schedule_once(lambda dt: self.show_error("No PDF loaded"))
                return
            
            # Get the page
            page = self.pdf_document[page_number - 1]
            
            # Mobile-optimized rendering with adaptive zoom
            mat = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            
            # Use lower quality for mobile performance
            pix = page.get_pixmap(matrix=mat, alpha=False)  # No alpha for better performance
            
            # Convert to PIL with mobile optimizations
            img_data = pix.tobytes("png")
            pil_image = Image.open(io.BytesIO(img_data))
            
            # For mobile, let Kivy handle the scaling to fit screen
            # Only resize if image is extremely large (memory constraint)
            if pil_image.width > 1600:  # Only resize very large images
                ratio = 1600 / pil_image.width
                new_height = int(pil_image.height * ratio)
                pil_image = pil_image.resize((1600, new_height), Image.Resampling.BILINEAR)
            
            # Optimize for mobile storage
            img_bytes = io.BytesIO()
            pil_image.save(img_bytes, format='JPEG', quality=85, optimize=True)  # JPEG for smaller size
            img_bytes.seek(0)
            
            # Cache with aggressive limits
            self.add_to_cache(page_number, img_bytes.getvalue())
            
            # Update UI
            Clock.schedule_once(lambda dt: self.display_page_image(img_bytes.getvalue(), 'jpeg'))
            
            # Cleanup PyMuPDF resources immediately
            pix = None
            page = None
            
            # Force garbage collection on mobile
            gc.collect()
                
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_error(f"Render error: {str(e)[:30]}"))
    
    def display_page_image(self, image_data, format='png'):
        """Display image with mobile optimizations"""
        try:
            core_image = CoreImage(io.BytesIO(image_data), ext=format)
            self.pdf_zoom.image.texture = core_image.texture
            
            # Reset zoom and position for new page
            self.pdf_zoom.fit_to_screen()
            
        except Exception as e:
            self.show_error(f"Display error: {str(e)[:30]}")
    
    def display_cached_page(self, page_number):
        """Display page from cache"""
        if page_number in self.page_cache:
            self.display_page_image(self.page_cache[page_number], 'jpeg')
    
    def add_to_cache(self, page_number, image_data):
        """Mobile-optimized caching with aggressive cleanup"""
        # Very aggressive cache management for mobile
        if len(self.page_cache) >= self.max_cache_size:
            # Remove all pages except current
            pages_to_remove = [p for p in self.page_cache.keys() if p != self.current_page]
            for p in pages_to_remove:
                del self.page_cache[p]
            
            # Force garbage collection
            gc.collect()
        
        self.page_cache[page_number] = image_data
    
    def cleanup_old_cache(self):
        """Aggressive cleanup for mobile memory management"""
        # Keep only current page and adjacent pages
        pages_to_keep = {self.current_page}
        if self.current_page > 1:
            pages_to_keep.add(self.current_page - 1)
        if self.current_page < self.total_pages:
            pages_to_keep.add(self.current_page + 1)
        
        pages_to_remove = [p for p in self.page_cache.keys() if p not in pages_to_keep]
        for p in pages_to_remove:
            del self.page_cache[p]
        
        # Force garbage collection
        gc.collect()
    
    def cleanup_resources(self):
        """Clean up all resources"""
        if self.pdf_document:
            self.pdf_document.close()
            self.pdf_document = None
        
        self.page_cache.clear()
        gc.collect()
    
    def show_loading(self):
        """Mobile-friendly loading indicator"""
        self.page_label.text = f"Loading {self.current_page}..."
    
    def show_error(self, message):
        """Display error message"""
        self.page_label.text = f"Error: {message}"
        self.pdf_zoom.image.texture = None
    
    def update_page_label(self):
        """Update page counter display"""
        if self.total_pages > 0:
            self.page_label.text = f"{self.current_page}/{self.total_pages}"
        else:
            self.page_label.text = "No PDF"
    
    def update_navigation_state(self):
        """Enable/disable navigation buttons"""
        if self.total_pages == 0:
            self.prev_btn.disabled = True
            self.next_btn.disabled = True
        else:
            self.prev_btn.disabled = (self.current_page <= 1)
            self.next_btn.disabled = (self.current_page >= self.total_pages)
    
    def jump_to_page(self, page_number):
        """Jump to specific page with mobile optimizations"""
        if 1 <= page_number <= self.total_pages:
            self.current_page = page_number
            self.update_page_label()
            self.update_navigation_state()
            self.render_page_async(page_number)
            self.cleanup_old_cache()
    
    def preload_adjacent_pages(self):
        """Simplified preloading for mobile"""
        # Only preload next page to save memory
        if (self.current_page < self.total_pages and 
            self.current_page + 1 not in self.page_cache):
            thread = Thread(target=self._render_page_thread, args=(self.current_page + 1,))
            thread.daemon = True
            thread.start()
    
    def get_pdf_info(self):
        """Get PDF information - same interface as desktop version"""
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
        """Cleanup on destruction"""
        self.cleanup_resources()