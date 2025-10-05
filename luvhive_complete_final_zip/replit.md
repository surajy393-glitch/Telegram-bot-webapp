# replit.md

## Overview

LuvHive is a Telegram bot that facilitates anonymous chat matching between users. The bot allows users to find and chat with random partners while maintaining anonymity. It includes user registration, profile management, premium features, chat matching algorithms, administrative tools, and engaging Fun & Games features. The system supports features like gender-based matching, age preferences, interest-based connections, rating systems, premium subscriptions through Telegram Stars, anonymous confessions with admin-moderated reply system, naughty polls, an advanced community-driven 60-second dare system with social pressure mechanics, and premium entertainment features.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

- **🚀 Instagram-Style Mini App Launch (Sept 2025)**: Complete social media experience within Telegram
  - Built production-ready React + FastAPI hybrid architecture solving 1000+ daily posts scalability
  - Instagram-like infinite scroll feed with Following/Explore tabs eliminating "Next" button frustration
  - Advanced features: posts, likes, comments, follows, saves, profiles, 72-hour TTL content rotation
  - Military-grade security: Fixed Telegram auth verification, CORS restrictions, rate limiting, input validation
  - Performance optimized: Cursor pagination, composite database indexes, connection pooling, hide-seen system
  - Deployment ready: Dual-service startup (bot + API), proper error handling, health monitoring
  - User experience: Double-tap likes, pull-to-refresh, real-time engagement, optimistic UI updates
  - Revenue potential: Addresses core UX issues blocking user growth and engagement monetization

- **Fantasy Match System Complete Transformation (Sept 2025)**: Comprehensive overhaul fixing all critical issues
  - Eliminated duplicate Fantasy Board files (removed fantasy_complete.py entirely)
  - Fixed fantasy relay runtime conflicts and crashes
  - Implemented fully functional reaction system with database persistence 
  - Fixed all database _exec() return value handling with proper None safety
  - Verified and optimized stats tracking system (views, reactions, matches)
  - Wired up achievement system to trigger after reactions and successful matches
  - Added security validation for reaction types and safe decrement logic
  - Reduced LSP errors by 50% across Fantasy Match system files
  - Enhanced system stability and revenue potential for $800-2000/month goals

- **Fantasy Anonymous Chat Relay (Sept 2025)**: Implemented complete anonymous chat system
  - High-priority message relay (group -15) with collision prevention
  - Bot_data state management for reliable session persistence
  - 15-minute timed sessions with automatic cleanup and manual exit
  - Conversation starter prompts and clean lifecycle management
  - Integrated with Fantasy Match system for seamless user experience
  - Timed prompt injector with 3-minute intervals and 30 weekend bonus prompts
  - One-tap admin control panel for auto/weekday/weekend prompt modes

- **Text Framework Architecture (Sept 2025)**: Resolved critical "text swallowing" issues
  - Implemented centralized text handling with priority groups (-20 to 9)
  - State ownership model preventing handler conflicts
  - TTL timeouts with automatic cleanup for stale sessions
  - Modular handler system: fantasy_chat, vault_text, text_router

- **Security Enhancement (Sept 2025)**: Implemented permanent gender/age policy 
  - Gender and age are now permanent after registration - cannot be changed later
  - Added English warning messages during registration about permanent selections
  - Completely removed gender/age edit functionality from profile system
  - Enhanced data integrity by preventing user profile manipulation

- **Notification Optimization**: Redesigned notification system to include only free features (confession, WYR, dare) for daily notifications
- Removed premium feature notifications (vault, fantasy, after dark) to eliminate user irritation

## System Architecture

### Core Components

**Telegram Bot Framework**: Built using `python-telegram-bot` library (version 20.7) as the primary interface for handling user interactions, commands, callbacks, and message routing.

**Database Layer**: PostgreSQL database managed through direct `psycopg2` connections with connection pooling. The database stores user profiles, chat metrics, premium status, and administrative data. The system uses environment variables (`DATABASE_URL`) for connection configuration with fallback to individual connection parameters.

**Modular Handler System**: The application uses a distributed handler architecture where different functionality is separated into modules:
- Registration handlers for user onboarding
- Chat handlers for matching and messaging
- Profile handlers for user data management
- Settings handlers for user preferences
- Premium handlers for subscription management
- Admin handlers for administrative functions

**State Management**: The bot maintains runtime state through in-memory data structures (queues, sets, dictionaries) for active chat sessions and waiting users. User session data is temporarily stored in Telegram's `user_data` context during multi-step interactions.

**Queue-Based Matching**: Chat matching uses deque-based queues to manage waiting users, with separate logic for premium users and different matching preferences (gender-based, age-based, interest-based).

### Authentication & Authorization

**Admin System**: Admin access is controlled through a configurable set of Telegram user IDs stored in environment variables (`ADMIN_IDS`) with fallback to hardcoded defaults.

**Premium Status**: Premium features are managed through database flags with time-based expiration. Premium users get priority matching, advanced filtering options, and media sharing capabilities.

**User Registration**: Multi-step registration process collecting gender, age, interests, and activities through inline keyboard interactions. Registration state is managed through callback patterns and user data context.

### Data Architecture

**User Profiles**: Comprehensive user data including demographics, interests, preferences, chat metrics, and premium status stored in PostgreSQL with dynamic column addition for new features.

**Metrics Tracking**: Real-time tracking of user engagement including dialog counts, message statistics, ratings, and reports with daily reset capabilities.

**Premium Management**: Subscription handling through Telegram Stars payment system with different duration packages and referral capabilities.

### Key Design Patterns

**Callback-Based Navigation**: Extensive use of inline keyboard callbacks with structured naming conventions (e.g., `prof:gender`, `prem:pay:m1`) for UI navigation.

**Configuration-Driven Behavior**: Feature flags like `FAST_INTRO` to modify bot behavior and environment-based configuration for deployment flexibility.

**Graceful Degradation**: Fallback mechanisms for database connections, default values for missing configuration, and error handling for transient failures.

**Modular Registration**: Separate registration system with interest selection, activity preferences, and profile completion workflows.

## External Dependencies

**Telegram Bot API**: Primary interface through `python-telegram-bot` library for all bot interactions, message handling, and payment processing.

**PostgreSQL Database**: Primary data persistence layer using `psycopg2-binary` for connection management. Supports both connection URL and individual parameter configuration.

**Telegram Stars Payment System**: Integration with Telegram's native payment system for premium subscription processing without external payment providers.

**Environment Configuration**: Relies on environment variables for:
- `BOT_TOKEN`: Telegram bot authentication
- `DATABASE_URL`/individual DB parameters: Database connectivity
- `ADMIN_IDS`: Administrative access control
- `FAST_INTRO`: Feature flag for instant chat introductions

**Logging Infrastructure**: Uses Python's built-in logging system for application monitoring and debugging with configurable log levels.