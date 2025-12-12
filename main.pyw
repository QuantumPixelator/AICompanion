import customtkinter as ctk
import requests
import json
import tkinter as tk
from tkinter import messagebox
import random
import os

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def create_tooltip(widget, text):
    """Create a tooltip for a widget"""
    def enter(event):
        tooltip = tk.Toplevel()
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry("+0+0")
        
        label = tk.Label(tooltip, text=text, background="#2b2b2b", foreground="white", 
                        relief="solid", borderwidth=1, font=("Arial", 10))
        label.pack()
        
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + widget.winfo_height() + 5
        tooltip.wm_geometry(f"+{x}+{y}")
        
        widget.tooltip = tooltip
    
    def leave(event):
        if hasattr(widget, 'tooltip'):
            widget.tooltip.destroy()
            del widget.tooltip
    
    widget.bind('<Enter>', enter)
    widget.bind('<Leave>', leave)

class ConversationCompanion:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("AI Companion")
        self.root.geometry("800x700")
        self.root.minsize(800, 700)
        self.root.maxsize(800, 700)

        self.load_personalities()
        self.load_config()
        self.conversation_history = []
        self.typing_buffer = ""

        # Main container
        main = ctk.CTkFrame(self.root)
        main.pack(fill="both", expand=True, padx=30, pady=30)

        # Title
        ctk.CTkLabel(main, text="AI Companion", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=(0, 25))

        # Personality
        personality_frame = ctk.CTkFrame(main, fg_color="transparent")
        personality_frame.pack(pady=(5, 10))
        ctk.CTkLabel(personality_frame, text="Personality:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0,10))
        self.personality_var = ctk.StringVar(value=self.selected_personality['name'])
        self.main_personality_combo = ctk.CTkComboBox(personality_frame, values=[p["name"] for p in self.personalities], 
                                                     variable=self.personality_var, width=200, height=30,
                                                     font=ctk.CTkFont(size=12), command=self.on_main_personality_select)
        self.main_personality_combo.pack(side="left", padx=(0,10))
        settings_btn = ctk.CTkButton(personality_frame, text="⚙️", command=self.manage_personalities, width=30, height=30,
                      font=ctk.CTkFont(size=12))
        settings_btn.pack(side="left")
        create_tooltip(settings_btn, "Manage personalities (add, edit, delete)")

        # Conversation display
        self.conversation_text = ctk.CTkTextbox(main, wrap="word", font=ctk.CTkFont(size=14), padx=20, pady=20,
                                         scrollbar_button_color="#555555", scrollbar_button_hover_color="#777777")
        self.conversation_text.pack(fill="both", expand=True, padx=50, pady=(5, 10))
        self.conversation_text.configure(state="disabled")  # Read-only
        self.conversation_text.tag_config("user", foreground="white")
        self.conversation_text.tag_config("ai", foreground="cyan")

        # Input frame
        input_frame = ctk.CTkFrame(main, fg_color="transparent")
        input_frame.pack(fill="x", padx=50, pady=(0, 10))
        self.message_entry = ctk.CTkEntry(input_frame, placeholder_text="Type your message here...", font=ctk.CTkFont(size=12))
        self.message_entry.pack(side="left", fill="x", expand=True)
        send_btn = ctk.CTkButton(input_frame, text="Send", command=self.send_message, width=80, height=30,
                      font=ctk.CTkFont(size=12))
        send_btn.pack(side="left", padx=(10,0))
        create_tooltip(send_btn, "Send your message to the AI")
        
        clear_btn = ctk.CTkButton(input_frame, text="Clear", command=self.clear_chat, width=80, height=30,
                      font=ctk.CTkFont(size=12))
        clear_btn.pack(side="left", padx=(10,0))
        create_tooltip(clear_btn, "Clear the conversation history")
        self.message_entry.bind("<Return>", lambda e: self.send_message())

    def send_message(self):
        user_message = self.message_entry.get().strip()
        if not user_message:
            return
        
        self.message_entry.delete(0, tk.END)
        
        # Add user message to history and display
        self.conversation_history.append({"role": "user", "content": user_message})
        self.display_conversation()
        
        # Prepare messages for API
        messages = [{"role": "system", "content": self.selected_personality["prompt"]}] + self.conversation_history
        
        try:
            # Load API key
            try:
                if not os.path.exists("api_key.json"):
                    raise FileNotFoundError("API key file not found")
                
                with open("api_key.json", "r") as f:
                    data = json.load(f)
                    api_key = data.get("api_key", "").strip()
                    
                if not api_key:
                    raise ValueError("API key is empty or missing")
                    
            except FileNotFoundError:
                error_msg = "API key file 'api_key.json' not found. Please create it with your API key."
                self.conversation_history.append({"role": "assistant", "content": f"Error: {error_msg}"})
                self.display_conversation()
                messagebox.showerror("Configuration Error", error_msg)
                return
            except json.JSONDecodeError:
                error_msg = "Invalid JSON format in api_key.json. Please check the file."
                self.conversation_history.append({"role": "assistant", "content": f"Error: {error_msg}"})
                self.display_conversation()
                messagebox.showerror("Configuration Error", error_msg)
                return
            except ValueError as ve:
                self.conversation_history.append({"role": "assistant", "content": f"Error: {str(ve)}"})
                self.display_conversation()
                messagebox.showerror("Configuration Error", str(ve))
                return
            
            # Make API request
            try:
                response = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": messages,
                        "max_tokens": 1000,
                        "temperature": 0.7,
                        "seed": random.randint(0, 1000000)
                    },
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                    timeout=60
                )
                response.raise_for_status()
                
            except requests.exceptions.Timeout:
                error_msg = "Request timed out. Please check your internet connection and try again."
                self.conversation_history.append({"role": "assistant", "content": f"Error: {error_msg}"})
                self.display_conversation()
                messagebox.showerror("Network Error", error_msg)
                return
            except requests.exceptions.ConnectionError:
                error_msg = "Connection failed. Please check your internet connection."
                self.conversation_history.append({"role": "assistant", "content": f"Error: {error_msg}"})
                self.display_conversation()
                messagebox.showerror("Network Error", error_msg)
                return
            except requests.exceptions.HTTPError as he:
                if response.status_code == 401:
                    error_msg = "Invalid API key. Please check your api_key.json file."
                elif response.status_code == 429:
                    error_msg = "Rate limit exceeded. Please wait a moment and try again."
                elif response.status_code >= 500:
                    error_msg = f"Server error ({response.status_code}). Please try again later."
                else:
                    error_msg = f"HTTP error {response.status_code}: {str(he)}"
                self.conversation_history.append({"role": "assistant", "content": f"Error: {error_msg}"})
                self.display_conversation()
                messagebox.showerror("API Error", error_msg)
                return
            
            # Parse response
            try:
                response_data = response.json()
                if "choices" not in response_data or not response_data["choices"]:
                    raise ValueError("Invalid response format from API")
                
                ai_message = response_data["choices"][0]["message"]["content"].strip()
                
                if not ai_message:
                    raise ValueError("Empty response from API")
                
            except (json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
                error_msg = f"Failed to parse API response: {str(e)}"
                self.conversation_history.append({"role": "assistant", "content": f"Error: {error_msg}"})
                self.display_conversation()
                messagebox.showerror("API Error", error_msg)
                return
            
            # Add AI response to history and start typing animation
            self.typing_buffer = ai_message
            self.conversation_history.append({"role": "assistant", "content": ""})
            self.conversation_text.configure(state="normal")
            self.conversation_text.insert("end", "AI: ", "ai")
            self.conversation_text.configure(state="disabled")
            self.type_message_char(0)
            
        except Exception as e:
            # Catch-all for unexpected errors
            error_msg = f"Unexpected error: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": f"Error: {error_msg}"})
            self.display_conversation()
            messagebox.showerror("Error", error_msg)

    def display_conversation(self):
        self.conversation_text.configure(state="normal")
        self.conversation_text.delete("1.0", "end")
        
        for msg in self.conversation_history:
            if msg["role"] == "user":
                self.conversation_text.insert("end", f"You: {msg['content']}\n\n", "user")
            elif msg["role"] == "assistant":
                self.conversation_text.insert("end", f"AI: {msg['content']}\n\n", "ai")
        
        self.conversation_text.configure(state="disabled")
        self.conversation_text.see("end")  # Scroll to bottom

    def type_message_char(self, char_index):
        if char_index < len(self.typing_buffer):
            char = self.typing_buffer[char_index]
            self.conversation_history[-1]["content"] += char
            self.conversation_text.configure(state="normal")
            self.conversation_text.insert("end", char, "ai")
            self.conversation_text.configure(state="disabled")
            self.conversation_text.see("end")
            self.root.after(15, self.type_message_char, char_index + 1)
        else:
            # Typing complete - clear and redisplay with markdown formatting
            self.typing_buffer = ""
            self.display_conversation()

    def clear_chat(self):
        self.conversation_history = []
        self.display_conversation()
        self.message_entry.delete(0, 'end')

    def run(self):
        self.root.mainloop()

    def load_personalities(self):
        try:
            if not os.path.exists("personalities.json"):
                raise FileNotFoundError("Personalities file not found")
            
            with open("personalities.json", "r") as f:
                self.personalities = json.load(f)
                
            # Validate personalities structure
            if not isinstance(self.personalities, list):
                raise ValueError("Invalid personalities format: expected a list")
            
            for i, p in enumerate(self.personalities):
                if not isinstance(p, dict) or "name" not in p or "prompt" not in p:
                    raise ValueError(f"Invalid personality at index {i}: missing 'name' or 'prompt'")
            
            if not self.personalities:
                raise ValueError("Personalities list is empty")
                
        except FileNotFoundError:
            self.personalities = [{"name": "General Conversationalist", "prompt": "You are a friendly and helpful conversational AI."}]
            self.save_personalities()
        except (json.JSONDecodeError, ValueError) as e:
            messagebox.showerror("Configuration Error", f"Error loading personalities: {str(e)}\n\nUsing default personality.")
            self.personalities = [{"name": "General Conversationalist", "prompt": "You are a friendly and helpful conversational AI."}]
            self.save_personalities()
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error loading personalities: {str(e)}\n\nUsing default personality.")
            self.personalities = [{"name": "General Conversationalist", "prompt": "You are a friendly and helpful conversational AI."}]
            self.save_personalities()

    def load_config(self):
        try:
            if not os.path.exists("config.json"):
                raise FileNotFoundError("Config file not found")
                
            with open("config.json", "r") as f:
                config = json.load(f)
                
            if not isinstance(config, dict):
                raise ValueError("Invalid config format: expected a dictionary")
                
            last_personality_name = config.get("last_personality", "")
            
            # Find the personality by name
            self.selected_personality = None
            for p in self.personalities:
                if p["name"] == last_personality_name:
                    self.selected_personality = p
                    break
            
            # Default to first personality if not found
            if not self.selected_personality:
                self.selected_personality = self.personalities[0] if self.personalities else {"name": "General", "prompt": "You are a helpful AI."}
                
        except FileNotFoundError:
            self.selected_personality = self.personalities[0] if self.personalities else {"name": "General", "prompt": "You are a helpful AI."}
        except json.JSONDecodeError as e:
            messagebox.showwarning("Configuration Warning", f"Error reading config file: {str(e)}\n\nUsing default personality.")
            self.selected_personality = self.personalities[0] if self.personalities else {"name": "General", "prompt": "You are a helpful AI."}
        except Exception as e:
            messagebox.showwarning("Configuration Warning", f"Unexpected error loading config: {str(e)}\n\nUsing default personality.")
            self.selected_personality = self.personalities[0] if self.personalities else {"name": "General", "prompt": "You are a helpful AI."}

    def save_config(self):
        try:
            config = {"last_personality": self.selected_personality["name"]}
            
            # Write to temporary file first, then rename (atomic operation)
            temp_file = "config.json.tmp"
            with open(temp_file, "w") as f:
                json.dump(config, f, indent=2)
            
            # Replace old file with new one
            if os.path.exists("config.json"):
                os.replace(temp_file, "config.json")
            else:
                os.rename(temp_file, "config.json")
                
        except (IOError, OSError) as e:
            messagebox.showerror("Save Error", f"Failed to save configuration: {str(e)}")
            # Clean up temp file if it exists
            if os.path.exists("config.json.tmp"):
                try:
                    os.remove("config.json.tmp")
                except:
                    pass
        except Exception as e:
            messagebox.showerror("Save Error", f"Unexpected error saving configuration: {str(e)}")

    def save_personalities(self):
        try:
            # Validate before saving
            if not isinstance(self.personalities, list):
                raise ValueError("Invalid personalities data structure")
            
            for i, p in enumerate(self.personalities):
                if not isinstance(p, dict) or "name" not in p or "prompt" not in p:
                    raise ValueError(f"Invalid personality at index {i}")
            
            # Write to temporary file first, then rename (atomic operation)
            temp_file = "personalities.json.tmp"
            with open(temp_file, "w") as f:
                json.dump(self.personalities, f, indent=2)
            
            # Replace old file with new one
            if os.path.exists("personalities.json"):
                os.replace(temp_file, "personalities.json")
            else:
                os.rename(temp_file, "personalities.json")
                
        except (IOError, OSError) as e:
            messagebox.showerror("Save Error", f"Failed to save personalities: {str(e)}")
            # Clean up temp file if it exists
            if os.path.exists("personalities.json.tmp"):
                try:
                    os.remove("personalities.json.tmp")
                except:
                    pass
        except ValueError as ve:
            messagebox.showerror("Validation Error", f"Invalid personality data: {str(ve)}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Unexpected error saving personalities: {str(e)}")

    def manage_personalities(self):
        window = ctk.CTkToplevel(self.root)
        window.title("Manage Personalities")
        window.geometry("575x475")
        window.transient(self.root)  # Make it a child window of main window
        window.grab_set()  # Make it modal
        
        # Center the window on the main window
        window.update_idletasks()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        popup_width = 575
        popup_height = 475
        x = main_x + (main_width - popup_width) // 2
        y = main_y + (main_height - popup_height) // 2
        window.geometry(f"575x475+{x}+{y}")
        
        # Handle window close
        def on_closing():
            window.grab_release()
            window.destroy()
        
        window.protocol("WM_DELETE_WINDOW", on_closing)
        
        # Dropdown for personalities
        ctk.CTkLabel(window, text="Select Personality", font=ctk.CTkFont(size=12)).pack(pady=(10,5))
        self.popup_personality_var = ctk.StringVar(value=self.personalities[0]["name"] if self.personalities else "")
        self.popup_personality_combo = ctk.CTkComboBox(window, values=[p["name"] for p in self.personalities], variable=self.popup_personality_var, width=300, height=30,
                        font=ctk.CTkFont(size=12), command=self.on_personality_select)
        self.popup_personality_combo.pack(pady=(0,10))
        
        # Name entry
        ctk.CTkLabel(window, text="Name", font=ctk.CTkFont(size=12)).pack(pady=(5,5))
        self.name_entry = ctk.CTkEntry(window, placeholder_text="Personality name", font=ctk.CTkFont(size=12))
        self.name_entry.pack(fill="x", padx=20, pady=(0,10))
        
        # Prompt entry
        ctk.CTkLabel(window, text="Prompt", font=ctk.CTkFont(size=12)).pack(pady=(5,5))
        self.prompt_entry = ctk.CTkTextbox(window, wrap="word", font=ctk.CTkFont(size=12), height=220)
        self.prompt_entry.pack(fill="x", padx=20, pady=(0,10))
        
        # Buttons
        btn_frame = ctk.CTkFrame(window, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0,10))
        add_btn = ctk.CTkButton(btn_frame, text="Add", command=self.add_personality)
        add_btn.pack(side="left", padx=(0,5))
        create_tooltip(add_btn, "Clear fields to add a new personality")
        
        self.accept_btn = ctk.CTkButton(btn_frame, text="Accept", command=self.accept_personality)
        self.accept_btn.pack(side="left", padx=(0,5))
        create_tooltip(self.accept_btn, "Save the new personality from the fields")
        
        update_btn = ctk.CTkButton(btn_frame, text="Update", command=self.edit_personality)
        update_btn.pack(side="left", padx=(0,5))
        create_tooltip(update_btn, "Update the selected personality with field changes")
        
        delete_btn = ctk.CTkButton(btn_frame, text="Delete", command=self.delete_personality, fg_color="#EF233C")
        delete_btn.pack(side="left", padx=(0,5))
        create_tooltip(delete_btn, "Delete the selected personality")
        
        # Initialize with first personality selected
        self.on_personality_select(self.popup_personality_var.get())

    def on_personality_select(self, name):
        for p in self.personalities:
            if p["name"] == name:
                self.name_entry.delete(0, tk.END)
                self.name_entry.insert(0, p["name"])
                self.prompt_entry.delete("1.0", "end")
                self.prompt_entry.insert("1.0", p["prompt"])
                break

    def add_personality(self):
        # Clear fields for new personality entry
        self.name_entry.delete(0, tk.END)
        self.prompt_entry.delete("1.0", "end")
        # Enable accept button
        self.accept_btn.configure(state="normal")

    def edit_personality(self):
        try:
            name = self.popup_personality_var.get()
            new_name = self.name_entry.get().strip()
            new_prompt = self.prompt_entry.get("1.0", "end").strip()
            
            # Validation
            if not new_name:
                messagebox.showerror("Validation Error", "Please enter a personality name.")
                return
            
            if not new_prompt:
                messagebox.showerror("Validation Error", "Please enter a personality prompt.")
                return
            
            if len(new_name) > 100:
                messagebox.showerror("Validation Error", "Personality name is too long (max 100 characters).")
                return
            
            if len(new_prompt) > 10000:
                messagebox.showerror("Validation Error", "Personality prompt is too long (max 10000 characters).")
                return
            
            # Check for duplicate name (excluding current personality)
            if new_name != name and any(p["name"] == new_name for p in self.personalities):
                messagebox.showerror("Duplicate Error", "A personality with this name already exists.")
                return
            
            # Find and update personality
            found = False
            for p in self.personalities:
                if p["name"] == name:
                    p["name"] = new_name
                    p["prompt"] = new_prompt
                    found = True
                    break
            
            if not found:
                messagebox.showerror("Error", f"Personality '{name}' not found.")
                return
            
            self.save_personalities()
            self.popup_personality_combo.configure(values=[p["name"] for p in self.personalities])
            self.popup_personality_var.set(new_name)
            self.on_personality_select(new_name)
            
            # Update main window dropdown
            self.main_personality_combo.configure(values=[p["name"] for p in self.personalities])
            if self.selected_personality["name"] == name:  # If editing the currently selected personality
                self.personality_var.set(new_name)
            
            messagebox.showinfo("Success", f"Personality '{new_name}' updated successfully.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to edit personality: {str(e)}")

    def delete_personality(self):
        try:
            name = self.popup_personality_var.get()
            
            if not name:
                messagebox.showerror("Error", "No personality selected.")
                return
            
            # Confirm deletion
            if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete the personality '{name}'?"):
                return
            
            # Check if personality exists
            if not any(p["name"] == name for p in self.personalities):
                messagebox.showerror("Error", f"Personality '{name}' not found.")
                return
            
            # Delete personality
            self.personalities = [p for p in self.personalities if p["name"] != name]
            
            # Ensure at least one personality exists
            if not self.personalities:
                self.personalities = [{"name": "General Conversationalist", "prompt": "You are a friendly and helpful conversational AI."}]
                messagebox.showinfo("Default Restored", "Last personality deleted. Default personality restored.")
            
            self.save_personalities()
            self.popup_personality_combo.configure(values=[p["name"] for p in self.personalities])
            self.popup_personality_var.set(self.personalities[0]["name"])
            self.on_personality_select(self.personalities[0]["name"])
            
            # Update main window dropdown
            self.main_personality_combo.configure(values=[p["name"] for p in self.personalities])
            if self.selected_personality["name"] == name:  # If deleting the currently selected personality
                self.personality_var.set(self.personalities[0]["name"])
                self.on_main_personality_select(self.personalities[0]["name"])
            
            messagebox.showinfo("Success", f"Personality '{name}' deleted successfully.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete personality: {str(e)}")

    def accept_personality(self):
        try:
            name = self.name_entry.get().strip()
            prompt = self.prompt_entry.get("1.0", "end").strip()
            
            # Validation
            if not name:
                messagebox.showerror("Validation Error", "Please enter a personality name.")
                return
            
            if not prompt:
                messagebox.showerror("Validation Error", "Please enter a personality prompt.")
                return
            
            if len(name) > 100:
                messagebox.showerror("Validation Error", "Personality name is too long (max 100 characters).")
                return
            
            if len(prompt) > 10000:
                messagebox.showerror("Validation Error", "Personality prompt is too long (max 10000 characters).")
                return
            
            if any(p["name"] == name for p in self.personalities):
                messagebox.showerror("Duplicate Error", "A personality with this name already exists.")
                return
            
            # Add personality
            self.personalities.append({"name": name, "prompt": prompt})
            self.save_personalities()
            self.popup_personality_combo.configure(values=[p["name"] for p in self.personalities])
            self.popup_personality_var.set(name)
            
            # Update main window dropdown
            self.main_personality_combo.configure(values=[p["name"] for p in self.personalities])
            self.personality_var.set(name)
            
            # Clear fields for next entry
            self.name_entry.delete(0, tk.END)
            self.prompt_entry.delete("1.0", "end")
            
            messagebox.showinfo("Success", f"Personality '{name}' added successfully.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add personality: {str(e)}")

    def on_main_personality_select(self, name):
        try:
            if not name:
                return
            
            # Find and set personality
            for p in self.personalities:
                if p["name"] == name:
                    self.selected_personality = p
                    self.save_config()
                    break
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to select personality: {str(e)}")

if __name__ == "__main__":
    app = ConversationCompanion()
    app.run()