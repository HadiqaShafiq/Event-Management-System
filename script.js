document.addEventListener("DOMContentLoaded", function () {
    const activateTab = function (tabName, clickedButton) {
        document.querySelectorAll(".tab-content").forEach(function (tab) {
            tab.classList.remove("active");
        });

        document.querySelectorAll(".tab-button").forEach(function (button) {
            button.classList.remove("active");
        });

        const selectedTab = document.getElementById(tabName);
        if (selectedTab) {
            selectedTab.classList.add("active");
        }

        if (clickedButton) {
            clickedButton.classList.add("active");
        }
    };

    document.querySelectorAll("[data-tab-target]").forEach(function (button) {
        button.addEventListener("click", function () {
            activateTab(this.dataset.tabTarget, this);
        });
    });

    document.querySelectorAll("[data-password-toggle]").forEach(function (checkbox) {
        checkbox.addEventListener("change", function () {
            const field = document.getElementById(this.dataset.passwordToggle);
            if (field) {
                field.type = this.checked ? "text" : "password";
            }
        });
    });

    const emailInput = document.querySelector("[data-check-email]");
    const emailResult = document.getElementById("emailCheckResult");

    if (emailInput && emailResult) {
        emailInput.addEventListener("blur", function () {
            const email = this.value.trim();

            if (!email) {
                emailResult.textContent = "";
                emailResult.className = "email-check-result";
                return;
            }

            fetch(`/check-email?email=${encodeURIComponent(email)}`)
                .then(function (response) {
                    return response.json();
                })
                .then(function (data) {
                    if (data.available) {
                        emailResult.textContent = "Available";
                        emailResult.className = "email-check-result available";
                    } else {
                        emailResult.textContent = data.message;
                        emailResult.className = "email-check-result unavailable";
                    }
                })
                .catch(function (error) {
                    console.error("Email availability check failed:", error);
                });
        });
    }

    const passwordStrengthInput = document.querySelector("[data-password-strength-source]");
    const passwordStrength = document.getElementById("passwordStrength");

    if (passwordStrengthInput && passwordStrength) {
        passwordStrengthInput.addEventListener("input", function () {
            const password = this.value;
            passwordStrength.className = "password-strength";

            if (!password) {
                passwordStrength.textContent = "";
                return;
            }

            let strength = 0;
            const feedback = [];

            if (password.length >= 8) {
                strength++;
            } else {
                feedback.push("At least 8 characters");
            }

            if (/[A-Z]/.test(password)) {
                strength++;
            } else {
                feedback.push("Add uppercase letters");
            }

            if (/[a-z]/.test(password)) {
                strength++;
            } else {
                feedback.push("Add lowercase letters");
            }

            if (/[0-9!@#$%^&*()\-_=+\[\]{}|;:,.<>?]/.test(password)) {
                strength++;
            } else {
                feedback.push("Add numbers or special characters");
            }

            let strengthLevel = "strong";
            let strengthText = "Strong password!";

            if (strength <= 1) {
                strengthLevel = "weak";
                strengthText = "Weak: " + feedback.join(", ");
            } else if (strength === 2 || strength === 3) {
                strengthLevel = "medium";
                strengthText = "Medium: " + (feedback.length > 0 ? feedback.join(", ") : "Good!");
            }

            passwordStrength.className = `password-strength ${strengthLevel}`;
            passwordStrength.textContent = strengthText;
        });
    }

    const signupForm = document.getElementById("signupForm");

    if (signupForm) {
        signupForm.addEventListener("submit", function (event) {
            const password = document.getElementById("signup-password");
            const confirmPassword = document.getElementById("confirm-password");
            const passwordError = document.getElementById("signupPasswordError");

            if (password && confirmPassword && password.value !== confirmPassword.value) {
                event.preventDefault();

                if (passwordError) {
                    passwordError.textContent = "Passwords do not match!";
                    passwordError.hidden = false;
                }

                return;
            }

            if (passwordError) {
                passwordError.textContent = "";
                passwordError.hidden = true;
            }
        });
    }

    document.querySelectorAll('input[type="file"]').forEach(function (input) {
        input.addEventListener("change", function () {
            const wrapper = input.closest(".file-input-wrapper") || input.closest(".file-upload-box") || input.parentElement;
            const fileNameText = wrapper ? wrapper.querySelector("#file-name") : document.getElementById("file-name");

            if (fileNameText) {
                fileNameText.textContent = this.files && this.files.length > 0 ? this.files[0].name : "No file chosen";
            }
        });
    });

    document.addEventListener("click", function (event) {
        const backButton = event.target.closest("[data-history-back]");

        if (backButton) {
            event.preventDefault();
            history.back();
        }
    });

    const chatbot = document.querySelector("[data-chatbot]");
    const eventDataScript = document.getElementById("chatbot-event-data");

    if (chatbot && eventDataScript) {
        const toggleButton = chatbot.querySelector(".chatbot-toggle");
        const closeButton = chatbot.querySelector(".chatbot-close");
        const form = chatbot.querySelector("[data-chatbot-form]");
        const input = form ? form.querySelector("input") : null;
        const messages = chatbot.querySelector("[data-chatbot-messages]");

        let events = [];

        try {
            events = JSON.parse(eventDataScript.textContent || "[]");
        } catch (error) {
            events = [];
        }

        const normalize = function (value) {
            return String(value || "").toLowerCase().replace(/[^a-z0-9\s]/g, " ").replace(/\s+/g, " ").trim();
        };

        const formatDateRange = function (event) {
            if (event.start_date && event.end_date && event.start_date !== event.end_date) {
                return `${event.start_date} to ${event.end_date}`;
            }

            return event.start_date || event.end_date || "date not added";
        };

        const formatPrice = function (event) {
            const price = Number(event.price || 0);
            return price > 0 ? `Rs. ${price}` : "Free";
        };

        const eventLine = function (event) {
            return `${event.title} is ${event.status.toLowerCase()} on ${formatDateRange(event)} at ${event.venue || "venue not added"}${event.city ? ", " + event.city : ""}. Price: ${formatPrice(event)}.`;
        };

        const findMatchingEvents = function (question) {
            const words = normalize(question).split(" ").filter(function (word) {
                return word.length > 2 && !["event", "events", "about", "tell", "show", "what", "when", "where", "price", "date", "venue", "city"].includes(word);
            });

            return events
                .map(function (event) {
                    const haystack = normalize([
                        event.title,
                        event.category,
                        event.venue,
                        event.city,
                        event.description,
                        event.status
                    ].join(" "));

                    const score = words.reduce(function (total, word) {
                        return total + (haystack.includes(word) ? 1 : 0);
                    }, 0);

                    return { event: event, score: score };
                })
                .filter(function (item) {
                    return item.score > 0;
                })
                .sort(function (a, b) {
                    return b.score - a.score;
                })
                .map(function (item) {
                    return item.event;
                });
        };

        const buildReply = function (question) {
            const text = normalize(question);
            const matches = findMatchingEvents(question);

            if (!text) {
                return "Please type your question and I will help.";
            }

            if (text.includes("hello") || text.includes("hi") || text.includes("hey")) {
                return "Hello! I can help you find events, explain booking, payment, reports, login, and admin features.";
            }

            if (text.includes("offline") || text.includes("internet")) {
                return "Yes, I work without internet. I use local website information and the events stored in this system database.";
            }

            if (matches.length > 0) {
                if (text.includes("where") || text.includes("venue") || text.includes("location") || text.includes("city")) {
                    return matches.slice(0, 3).map(function (event) {
                        return `${event.title}: ${event.venue || "venue not added"}${event.city ? ", " + event.city : ""}.`;
                    }).join(" ");
                }

                if (text.includes("when") || text.includes("date") || text.includes("time")) {
                    return matches.slice(0, 3).map(function (event) {
                        return `${event.title}: ${formatDateRange(event)}.`;
                    }).join(" ");
                }

                if (text.includes("price") || text.includes("fee") || text.includes("cost") || text.includes("free")) {
                    return matches.slice(0, 3).map(function (event) {
                        return `${event.title}: ${formatPrice(event)}.`;
                    }).join(" ");
                }

                return matches.slice(0, 3).map(eventLine).join(" ");
            }

            if (text.includes("upcoming") || text.includes("available") || text.includes("all events") || text.includes("events")) {
                const visibleEvents = events.filter(function (event) {
                    return event.status !== "Ended";
                }).slice(0, 5);

                if (visibleEvents.length === 0) {
                    return "No upcoming or ongoing events are available right now. Please check the events page again later.";
                }

                return "Available events: " + visibleEvents.map(function (event) {
                    return `${event.title} (${event.status}, ${formatDateRange(event)})`;
                }).join("; ") + ".";
            }

            if (text.includes("book") || text.includes("booking") || text.includes("reserve")) {
                return "To book an event, login as a user, open Events, choose an event, then click Book. Paid events will send you to the payment page first.";
            }

            if (text.includes("payment") || text.includes("receipt") || text.includes("paid")) {
                return "For paid events, upload a valid payment receipt image on the payment page. Free events are booked directly without payment.";
            }

            if (text.includes("register") || text.includes("signup") || text.includes("sign up") || text.includes("account")) {
                return "Open Login, switch to registration, fill your details, and submit. Your account may need admin approval before you can login.";
            }

            if (text.includes("login") || text.includes("password")) {
                return "Use the Login page with your registered email and password. If registration is pending, wait for admin approval.";
            }

            if (text.includes("report") || text.includes("issue") || text.includes("complaint")) {
                return "Users can report an event issue from the Reports section. Admins can review submitted reports from the admin dashboard.";
            }

            if (text.includes("admin") || text.includes("manage")) {
                return "Admins can add, edit, and delete events, approve users, review bookings, and handle reports from the admin area.";
            }

            if (text.includes("contact") || text.includes("phone")) {
                return "Event contact numbers are shown in each event's details when the admin has added them.";
            }

            return "I can answer questions about events, dates, venues, prices, booking, payment, reports, registration, and admin/user features. Try asking: What events are available?";
        };

        const addMessage = function (text, sender) {
            const message = document.createElement("div");
            message.className = `chatbot-message ${sender}`;
            message.textContent = text;
            messages.appendChild(message);
            messages.scrollTop = messages.scrollHeight;
        };

        const setOpen = function (isOpen) {
            chatbot.classList.toggle("is-open", isOpen);
            toggleButton.setAttribute("aria-expanded", String(isOpen));

            if (isOpen && input) {
                input.focus();
            }
        };

        toggleButton.addEventListener("click", function () {
            setOpen(!chatbot.classList.contains("is-open"));
        });

        closeButton.addEventListener("click", function () {
            setOpen(false);
        });

        form.addEventListener("submit", function (event) {
            event.preventDefault();

            const question = input.value.trim();

            if (!question) {
                return;
            }

            addMessage(question, "user");
            input.value = "";

            window.setTimeout(function () {
                addMessage(buildReply(question), "bot");
            }, 180);
        });
    }
});

