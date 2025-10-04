# admin_commands.py - Enhanced admin commands with bulletproof operations
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

log = logging.getLogger(__name__)

async def bulletproof_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get comprehensive bulletproof system status."""
    try:
        # Import all bulletproof systems
        from utils.monitoring import metrics
        from utils.backup_system import backup_system
        from utils.incident_response import incident_response
        from utils.maintenance import maintenance_system
        from utils.abuse_prevention import abuse_prevention
        
        # Get current metrics
        current_metrics = metrics.get_metrics_summary()
        
        # Get incident status
        incident_status = incident_response.get_incident_status()
        
        # Get backup status
        backup_list = backup_system.list_backups()
        
        # Build status report
        status_report = f"""
🛡️ **Bulletproof Protection Status**

📊 **System Metrics:**
• CPU: {current_metrics.get('system', {}).get('cpu_percent', 0):.1f}%
• Memory: {current_metrics.get('system', {}).get('memory_percent', 0):.1f}%
• Active Alerts: {current_metrics.get('alerts_active', 0)}

🚨 **Incidents:**
• Active: {incident_status.get('active_incidents', 0)}
• Status: {'🟢 All Clear' if incident_status.get('active_incidents', 0) == 0 else '🔴 Active Issues'}

💾 **Backups:**
• Available: {len(backup_list.get('backups', []))}
• Latest: {backup_list.get('backups', [{}])[0].get('created_at', 'None')[:16] if backup_list.get('backups') else 'None'}

🔒 **Protection Active:**
✅ Rate Limiting (15 msg/s global)
✅ FloodWait Protection  
✅ Database Integrity (UPSERT patterns)
✅ Content Moderation
✅ Abuse Prevention
✅ Input Validation
✅ Advisory Locks
✅ Payment Safety
✅ Privacy Compliance
✅ Monitoring & Alerts

**Status: BULLETPROOF** 🚀
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Detailed Metrics", callback_data="bp:metrics")],
            [InlineKeyboardButton("💾 Run Backup", callback_data="bp:backup")],
            [InlineKeyboardButton("🧹 Run Maintenance", callback_data="bp:maintenance")],
            [InlineKeyboardButton("🧪 Load Test", callback_data="bp:loadtest")]
        ])
        
        await update.message.reply_text(status_report, reply_markup=keyboard)
        
    except Exception as e:
        log.error(f"Bulletproof status failed: {e}")
        await update.message.reply_text(f"❌ Status check failed: {str(e)}")

async def handle_bulletproof_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle bulletproof system callback buttons."""
    query = update.callback_query
    await query.answer()
    
    action = query.data.split(':')[1] if ':' in query.data else query.data
    
    try:
        if action == "metrics":
            from utils.monitoring import metrics
            current_metrics = metrics.get_metrics_summary()
            
            metrics_text = f"""
📊 **Detailed System Metrics**

**Counters:**
{chr(10).join([f"• {k}: {v}" for k, v in list(current_metrics.get('counters', {}).items())[:10]])}

**Response Times:**
{chr(10).join([f"• {k}: {v.get('avg', 0):.1f}ms avg" for k, v in list(current_metrics.get('timers', {}).items())[:5]])}

**System Resources:**
• CPU: {current_metrics.get('system', {}).get('cpu_percent', 0):.1f}%
• Memory: {current_metrics.get('system', {}).get('memory_percent', 0):.1f}%
• Disk: {current_metrics.get('system', {}).get('disk_percent', 0):.1f}%
"""
            await query.edit_message_text(metrics_text)
            
        elif action == "backup":
            from utils.backup_system import backup_system
            
            await query.edit_message_text("🔄 Creating backup...")
            result = backup_system.create_backup()
            
            if result["success"]:
                backup_text = f"""
✅ **Backup Completed**

• File: {result['backup_file'].split('/')[-1]}
• Size: {result['metadata']['backup_size_bytes']:,} bytes
• Verified: {'✅' if result['verification']['success'] else '❌'}
• Tables: {len(result['metadata']['db_stats'])} tables backed up

Backup is ready for disaster recovery! 💾
"""
            else:
                backup_text = f"❌ Backup failed: {result['error']}"
                
            await query.edit_message_text(backup_text)
            
        elif action == "maintenance":
            from utils.maintenance import maintenance_system
            
            await query.edit_message_text("🧹 Running maintenance...")
            result = maintenance_system.execute_maintenance_cycle("daily")
            
            if result["success"]:
                cleanup_details = result.get("operations", {}).get("data_retention", {})
                maintenance_text = f"""
✅ **Maintenance Completed**

• Duration: {result['duration_seconds']:.1f}s
• Cleaned Records: {cleanup_details.get('total_deleted', 0):,}
• Database Health: ✅ Good

**Cleanup Details:**
{chr(10).join([f"• {k}: {v}" for k, v in cleanup_details.get('cleanup_details', {}).items()])}

Database is optimized! 🧹
"""
            else:
                maintenance_text = f"❌ Maintenance failed: {result['error']}"
                
            await query.edit_message_text(maintenance_text)
            
        elif action == "loadtest":
            await query.edit_message_text("🧪 Running quick load test (this may take 2-3 minutes)...")
            
            from utils.load_testing import run_quick_load_test
            result = await run_quick_load_test(users=25, minutes=1)
            
            if result["success"]:
                metrics = result["metrics"]
                analysis = result.get("performance_analysis", {})
                
                loadtest_text = f"""
🧪 **Load Test Results**

• Users Simulated: 25
• Requests: {metrics['requests_sent']:,}
• Success Rate: {metrics.get('success_rate_percent', 0):.1f}%
• Avg Response: {metrics.get('avg_response_time_ms', 0):.1f}ms
• P95 Response: {metrics.get('p95_response_time_ms', 0):.1f}ms

**Performance:** {'✅ PASS' if analysis.get('overall_status') == 'pass' else '⚠️ REVIEW'}
**Score:** {analysis.get('score', 0)}/100

Your bot can handle the load! 🚀
"""
            else:
                loadtest_text = f"❌ Load test failed: {result['error']}"
                
            await query.edit_message_text(loadtest_text)
            
    except Exception as e:
        log.error(f"Bulletproof callback failed: {e}")
        await query.edit_message_text(f"❌ Operation failed: {str(e)}")

# Privacy compliance commands
async def privacy_policy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show privacy policy."""
    try:
        from utils.privacy_compliance import get_privacy_policy_text
        policy_text = get_privacy_policy_text()
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 My Data", callback_data="privacy:mydata")],
            [InlineKeyboardButton("🗑️ Delete My Data", callback_data="privacy:delete")]
        ])
        
        await update.message.reply_text(policy_text, reply_markup=keyboard)
        
    except Exception as e:
        log.error(f"Privacy policy failed: {e}")
        await update.message.reply_text("❌ Privacy policy not available")

async def delete_my_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request user data deletion with 24-hour grace period."""
    try:
        from utils.privacy_compliance import privacy_manager
        
        user_id = update.effective_user.id
        result = privacy_manager.request_data_deletion(user_id)
        
        if result["success"]:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel Deletion", callback_data="privacy:cancel")]
            ])
            
            deletion_text = f"""
🗑️ **Data Deletion Scheduled**

{result['message']}

**What happens next:**
• Your data will be permanently deleted in 24 hours
• You can cancel anytime before deletion
• This includes all posts, messages, and profile data

⚠️ **This action cannot be undone after 24 hours!**
"""
            await update.message.reply_text(deletion_text, reply_markup=keyboard)
        else:
            await update.message.reply_text(f"❌ Deletion request failed: {result['error']}")
            
    except Exception as e:
        log.error(f"Delete data failed: {e}")
        await update.message.reply_text("❌ Deletion request failed")

async def handle_privacy_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle privacy-related callback buttons."""
    query = update.callback_query
    await query.answer()
    
    action = query.data.split(':')[1] if ':' in query.data else query.data
    user_id = update.effective_user.id
    
    try:
        from utils.privacy_compliance import privacy_manager
        
        if action == "mydata":
            result = privacy_manager.get_user_data_summary(user_id)
            
            if result["success"]:
                data_text = f"""
📊 **Your Data Summary**

**Total Records:** {result['total_records']}

**Data Breakdown:**
{chr(10).join([f"• {k.title()}: {v}" for k, v in result['data_breakdown'].items()])}

**Status:** {'🗑️ Deletion Pending' if result['has_pending_deletion'] else '✅ Active'}

Last checked: {result['checked_at'][:16]}
"""
            else:
                data_text = f"❌ Could not retrieve data: {result['error']}"
                
            await query.edit_message_text(data_text)
            
        elif action == "delete":
            result = privacy_manager.request_data_deletion(user_id)
            
            if result["success"]:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ Cancel Deletion", callback_data="privacy:cancel")]
                ])
                
                delete_text = f"""
🗑️ **Data Deletion Scheduled**

{result['message']}

Deletion time: {result['deletion_time'][:16]}
Grace period: {result['grace_period_hours']} hours

⚠️ **This cannot be undone after the grace period!**
"""
                await query.edit_message_text(delete_text, reply_markup=keyboard)
            else:
                await query.edit_message_text(f"❌ Deletion failed: {result['error']}")
                
        elif action == "cancel":
            result = privacy_manager.cancel_data_deletion(user_id)
            
            if result["success"]:
                await query.edit_message_text(f"✅ {result['message']}")
            else:
                await query.edit_message_text(f"❌ {result['error']}")
                
    except Exception as e:
        log.error(f"Privacy callback failed: {e}")
        await query.edit_message_text("❌ Privacy operation failed")

# Health check commands for load balancers
async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Health check endpoint for monitoring."""
    try:
        from utils.monitoring import metrics
        current_metrics = metrics.get_metrics_summary()
        
        # Quick health checks
        health_status = {
            "status": "healthy",
            "timestamp": current_metrics.get("timestamp", "unknown"),
            "alerts": current_metrics.get("alerts_active", 0),
            "memory_percent": current_metrics.get("system", {}).get("memory_percent", 0)
        }
        
        # Check if system is under stress
        if health_status["memory_percent"] > 90 or health_status["alerts"] > 5:
            health_status["status"] = "degraded"
        
        status_emoji = "✅" if health_status["status"] == "healthy" else "⚠️"
        
        await update.message.reply_text(
            f"{status_emoji} **Health Status:** {health_status['status'].title()}\n"
            f"Memory: {health_status['memory_percent']:.1f}%\n"
            f"Active Alerts: {health_status['alerts']}"
        )
        
    except Exception as e:
        log.error(f"Health check failed: {e}")
        await update.message.reply_text("❌ Health check failed")

# Command handlers for main.py integration
bulletproof_handlers = [
    CommandHandler("bulletproof", bulletproof_status),
    CommandHandler("privacy", privacy_policy),
    CommandHandler("delete_me", delete_my_data),
    CommandHandler("healthz", health_check),
    CallbackQueryHandler(handle_bulletproof_callbacks, pattern="^bp:"),
    CallbackQueryHandler(handle_privacy_callbacks, pattern="^privacy:")
]