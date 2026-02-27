/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/**
 * Captures image from webcam, resizes to max 320px width,
 * converts to webp at 50% quality, returns base64 string.
 */
async function captureAndCompressPhoto() {
    return new Promise((resolve, reject) => {
        let stream = null;
        let video = null;

        navigator.mediaDevices
            .getUserMedia({ video: { facingMode: "user", width: { ideal: 640 } } })
            .then((mediaStream) => {
                stream = mediaStream;
                video = document.createElement("video");
                video.srcObject = stream;
                video.setAttribute("playsinline", true);
                video.muted = true;

                video.onloadedmetadata = () => {
                    video.play();
                    // Small delay to let camera warm up
                    setTimeout(() => {
                        try {
                            const canvas = document.createElement("canvas");
                            const maxWidth = 320;
                            const scale = Math.min(1, maxWidth / video.videoWidth);
                            canvas.width = video.videoWidth * scale;
                            canvas.height = video.videoHeight * scale;

                            const ctx = canvas.getContext("2d");
                            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

                            // Convert to webp at 50% quality
                            const dataURL = canvas.toDataURL("image/webp", 0.5);
                            // Strip the data URI prefix to get raw base64
                            const base64 = dataURL.split(",")[1] || "";

                            // Clean up
                            stream.getTracks().forEach((t) => t.stop());
                            resolve(base64);
                        } catch (err) {
                            stream.getTracks().forEach((t) => t.stop());
                            reject(err);
                        }
                    }, 800);
                };
            })
            .catch((err) => {
                // Camera not available - resolve empty (attendance still possible)
                console.warn("my_hr: Camera not available:", err.message);
                resolve("");
            });
    });
}

/**
 * Get current GPS coordinates.
 * Returns { latitude, longitude } or { latitude: 0, longitude: 0 } on failure.
 */
function getCurrentPosition() {
    return new Promise((resolve) => {
        if (!navigator.geolocation) {
            resolve({ latitude: 0, longitude: 0 });
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                resolve({
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude,
                });
            },
            (err) => {
                console.warn("my_hr: Geolocation error:", err.message);
                resolve({ latitude: 0, longitude: 0 });
            },
            { timeout: 8000, maximumAge: 60000 }
        );
    });
}

class SystrayCheckin extends Component {
    static template = "my_hr.SystrayCheckin";
    static props = {};

    setup() {
        this.notification = useService("notification");
        this.rpc = useService("rpc");

        this.state = useState({
            checkedIn: false,
            checkInTime: "",
            loading: false,
        });

        this._pollInterval = null;
        onMounted(() => this._loadStatus());
        onWillUnmount(() => {
            if (this._pollInterval) clearInterval(this._pollInterval);
        });
    }

    async _loadStatus() {
        try {
            const result = await this.rpc("/my_hr/attendance/status", {});
            if (result) {
                this.state.checkedIn = result.checked_in || false;
                this.state.checkInTime = result.check_in_time || "";
            }
        } catch (e) {
            // Silently fail on status load
        }
    }

    async onClick() {
        if (this.state.loading) return;
        this.state.loading = true;

        try {
            // Get location and photo in parallel
            const [position, photo] = await Promise.all([
                getCurrentPosition(),
                captureAndCompressPhoto(),
            ]);

            const result = await this.rpc("/my_hr/attendance/check", {
                latitude: position.latitude,
                longitude: position.longitude,
                photo: photo,
                user_agent: navigator.userAgent || "",
            });

            if (result.success) {
                const action = result.action;
                const time = result.timestamp || "";
                this.state.checkedIn = action === "check_in";
                this.state.checkInTime = action === "check_in" ? time.slice(11, 16) : "";

                this.notification.add(
                    action === "check_in"
                        ? _t("Checked in successfully at %(time)s", { time: time.slice(11, 16) })
                        : _t("Checked out successfully at %(time)s", { time: time.slice(11, 16) }),
                    { type: "success", sticky: false }
                );
            } else {
                this.notification.add(
                    result.error || _t("Attendance failed. Please try again."),
                    { type: "danger", sticky: true }
                );
            }
        } catch (err) {
            this.notification.add(
                _t("An unexpected error occurred. Please try again."),
                { type: "danger" }
            );
            console.error("my_hr check-in error:", err);
        } finally {
            this.state.loading = false;
        }
    }
}

// Register in the systray
registry.category("systray").add(
    "my_hr.SystrayCheckin",
    { Component: SystrayCheckin },
    { sequence: 1 }
);

export { SystrayCheckin };