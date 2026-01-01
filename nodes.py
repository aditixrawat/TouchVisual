import cv2
import numpy as np

# =========================
# Base Node
# =========================
class Node:
    def process(self, frame):
        return frame


# =========================
# Feedback Node
# =========================
class FeedbackNode(Node):
    def __init__(self, decay=0.9):
        self.decay = decay
        self.buffer = None

    def process(self, frame):
        frame_f = frame.astype(np.float32)
        if self.buffer is None:
            self.buffer = frame_f.copy()
        else:
            self.buffer = self.buffer * self.decay + frame_f * (1 - self.decay)

        return np.clip(self.buffer, 0, 255).astype(np.uint8)


# =========================
# Glow Node
# =========================
class GlowNode(Node):
    def __init__(self, strength=1.5, blur_size=21):
        self.strength = strength
        self.blur_size = blur_size

    def process(self, frame):
        blurred = cv2.GaussianBlur(frame, (self.blur_size, self.blur_size), 0)
        return cv2.addWeighted(frame, 1.0, blurred, self.strength, 0)


# =========================
# RGB Split Node
# =========================
class RGBSplitNode(Node):
    def __init__(self, shift=10):
        self.shift = shift

    def process(self, frame):
        b, g, r = cv2.split(frame)
        r = np.roll(r, self.shift, axis=1)
        b = np.roll(b, -self.shift, axis=0)
        return cv2.merge([b, g, r])


# =========================
# Object Tracking Node
# =========================
class ObjectTrackingNode(Node):
    def __init__(self, tracker_type='CSRT', show_trail=True, trail_length=20):
        self.tracker_type = tracker_type
        self.show_trail = show_trail
        self.trail_length = trail_length
        self.tracker = None
        self.bbox = None
        self.trail_points = []
        self.tracker_initialized = False
        self.use_contrib_tracker = False
        self.last_bbox = None
        
        # Check if contrib trackers are available
        self._check_tracker_availability()
        
    def _check_tracker_availability(self):
        """Check if OpenCV contrib trackers are available"""
        try:
            _ = cv2.TrackerCSRT_create()
            self.use_contrib_tracker = True
        except AttributeError:
            self.use_contrib_tracker = False
            print("OpenCV contrib trackers not available. Using fallback tracking method.")
        
    def init_tracker(self, frame, bbox):
        """Initialize tracker with bounding box"""
        if self.use_contrib_tracker:
            try:
                if self.tracker_type == 'CSRT':
                    self.tracker = cv2.TrackerCSRT_create()
                elif self.tracker_type == 'KCF':
                    self.tracker = cv2.TrackerKCF_create()
                else:
                    self.tracker = cv2.TrackerCSRT_create()
                
                if self.tracker:
                    self.tracker.init(frame, bbox)
                    self.bbox = bbox
                    self.last_bbox = bbox
                    self.tracker_initialized = True
            except (AttributeError, cv2.error) as e:
                print(f"Tracker initialization failed: {e}")
                self.tracker = None
                self.tracker_initialized = False
        else:
            # Use fallback: store bbox for centroid-based tracking
            self.bbox = bbox
            self.last_bbox = bbox
            self.tracker_initialized = True
        
    def auto_detect_object(self, frame):
        """Auto-detect largest moving object using background subtraction"""
        if not hasattr(self, 'bg_subtractor'):
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        
        fg_mask = self.bg_subtractor.apply(frame)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        
        # Handle different OpenCV versions
        try:
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        except ValueError:
            # OpenCV 3.x returns 3 values
            _, contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest_contour) > 500:
                x, y, w, h = cv2.boundingRect(largest_contour)
                return (x, y, w, h)
        return None
    
    def process(self, frame):
        if frame is None or frame.size == 0:
            return frame
        
        result = frame.copy()
        
        # Auto-initialize tracker if not initialized
        if not self.tracker_initialized:
            bbox = self.auto_detect_object(frame)
            if bbox:
                self.init_tracker(frame, bbox)
        
        # Track object if initialized
        if self.tracker_initialized:
            bbox = None
            success = False
            
            if self.use_contrib_tracker and self.tracker:
                # Use contrib tracker if available
                try:
                    success, bbox = self.tracker.update(frame)
                except (AttributeError, cv2.error):
                    success = False
                    bbox = None
            else:
                # Fallback: use background subtraction for tracking
                bbox = self.auto_detect_object(frame)
                if bbox:
                    # Calculate distance from last bbox to determine if it's the same object
                    if self.last_bbox:
                        last_center = (self.last_bbox[0] + self.last_bbox[2]//2, 
                                      self.last_bbox[1] + self.last_bbox[3]//2)
                        new_center = (bbox[0] + bbox[2]//2, bbox[1] + bbox[3]//2)
                        distance = np.sqrt((last_center[0] - new_center[0])**2 + 
                                          (last_center[1] - new_center[1])**2)
                        # If close enough, consider it the same object
                        if distance < 100:  # Threshold for object continuity
                            success = True
                            self.last_bbox = bbox
                        else:
                            # New object detected, update
                            success = True
                            self.last_bbox = bbox
                    else:
                        success = True
                        self.last_bbox = bbox
            
            if success and bbox:
                self.bbox = bbox
                x, y, w, h = [int(v) for v in bbox]
                center = (x + w // 2, y + h // 2)
                
                # Add to trail
                if self.show_trail:
                    self.trail_points.append(center)
                    if len(self.trail_points) > self.trail_length:
                        self.trail_points.pop(0)
                    
                    # Draw trail
                    for i in range(1, len(self.trail_points)):
                        thickness = max(1, int(2 * (i / len(self.trail_points))))
                        cv2.line(result, self.trail_points[i-1], self.trail_points[i], 
                                (0, 255, 0), thickness)
                
                # Draw bounding box
                cv2.rectangle(result, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.circle(result, center, 5, (0, 255, 0), -1)
            else:
                # Tracking lost, try to reinitialize
                if not self.use_contrib_tracker:
                    # For fallback method, just reset and try again next frame
                    self.last_bbox = None
                else:
                    self.tracker_initialized = False
                    self.tracker = None
                    self.trail_points = []
        
        return result


# =========================
# Blob Tracking Node
# =========================
class BlobTrackingNode(Node):
    def __init__(self, min_area=100, max_area=50000, show_contours=True, 
                 show_centroids=True, color=(255, 0, 255)):
        self.min_area = min_area
        self.max_area = max_area
        self.show_contours = show_contours
        self.show_centroids = show_centroids
        self.color = color
        self.bg_subtractor = None
        
    def process(self, frame):
        if frame is None or frame.size == 0:
            return frame
        
        if self.bg_subtractor is None:
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500, varThreshold=50, detectShadows=True
            )
        
        result = frame.copy()
        
        # Apply background subtraction
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Morphological operations to clean up mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours - handle different OpenCV versions
        try:
            contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        except ValueError:
            # OpenCV 3.x returns 3 values
            _, contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter and draw blobs
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_area <= area <= self.max_area:
                # Draw contour
                if self.show_contours:
                    cv2.drawContours(result, [contour], -1, self.color, 2)
                
                # Calculate centroid
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    
                    # Draw centroid
                    if self.show_centroids:
                        cv2.circle(result, (cx, cy), 8, self.color, -1)
                    
                    # Draw bounding box
                    x, y, w, h = cv2.boundingRect(contour)
                    cv2.rectangle(result, (x, y), (x + w, y + h), self.color, 2)
                    
                    # Draw area text
                    cv2.putText(result, f"{int(area)}", (x, y - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.color, 2)
        
        return result