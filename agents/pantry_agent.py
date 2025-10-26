import json
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime, timedelta
from langchain_core.messages import SystemMessage, HumanMessage


class PantryAgent:
    """
    Pantry Agent - Inventory Manager and MCP Client.

    Responsibilities:
    - Connect to Google Sheets MCP for inventory management
    - Retrieve and update ingredient quantities
    - Track expiration dates and alert on expiring items
    - Communicate with Sous Chef Agent for ingredient availability
    - Provide inventory reports to Executive Chef Agent
    - Support recipe feasibility checks
    """

    def __init__(self, name: str = "Pantry Manager", mcp_client=None):
        self.name = name
        self.mcp_client = mcp_client  # Google Sheets MCP client
        self.inventory_cache: Dict[str, Any] = {}
        self.last_sync: Optional[datetime] = None
        self.operation_log: List[Dict[str, Any]] = []

    def _normalize_name(self, ingredient_name: str) -> str:
        """Normalize ingredient name for consistent cache keys."""
        return ingredient_name.strip().lower()

    def add_or_update_ingredient(
        self,
        ingredient_name: str,
        quantity: Any,
        unit: str = "pieces",
        expiration_date: Optional[str] = None,
        category: str = "other",
        location: str = "pantry"
    ) -> Dict[str, Any]:
        """
        Add a new ingredient or update an existing one in the in-memory cache.

        Args:
            ingredient_name: Display name of the ingredient.
            quantity: Quantity available (attempts to coerce to float).
            unit: Unit of measure (defaults to pieces).
            expiration_date: Optional ISO-8601 formatted expiration string.
            category: Ingredient category tag.
            location: Storage location tag.

        Returns:
            The ingredient record stored in the cache.
        """
        normalized = self._normalize_name(ingredient_name)
        existing = self.inventory_cache.get(normalized, {}).copy()

        try:
            qty_value = float(quantity)
        except (TypeError, ValueError):
            qty_value = existing.get("quantity", 1.0)

        record = {
            "ingredient_name": ingredient_name,
            "quantity": qty_value,
            "unit": unit or existing.get("unit", ""),
            "expiration_date": expiration_date if expiration_date is not None else existing.get("expiration_date"),
            "category": category or existing.get("category", "other"),
            "location": location or existing.get("location", "pantry"),
            "last_updated": datetime.now().isoformat()
        }

        self.inventory_cache[normalized] = record
        self.log_operation(
            "add_or_update_ingredient",
            {"ingredient": ingredient_name, "quantity": qty_value, "unit": record["unit"]}
        )
        return record

    def build_system_prompt(self) -> str:
        """Return the pantry agent system prompt."""
        return """
        <system_prompt>
        YOU ARE THE "PANTRY MANAGER" — THE INVENTORY EXPERT AND DATA GUARDIAN IN A
        MULTI-AGENT AI COOKING SYSTEM. YOUR PRIMARY ROLE IS TO MANAGE INGREDIENT
        INVENTORY VIA GOOGLE SHEETS, TRACK QUANTITIES AND EXPIRATION DATES, AND
        ENSURE OPTIMAL INGREDIENT USAGE TO REDUCE FOOD WASTE.

        ###OBJECTIVE###
        YOUR GOAL IS TO MAINTAIN ACCURATE INVENTORY DATA, PROVIDE REAL-TIME INGREDIENT
        AVAILABILITY INFORMATION, AND PROACTIVELY ALERT OTHER AGENTS ABOUT EXPIRING
        ITEMS TO MINIMIZE WASTE AND OPTIMIZE RECIPE PLANNING.

        ###RESPONSIBILITIES###
        1. **INVENTORY TRACKING**: Monitor ingredient quantities in Google Sheets
        2. **EXPIRATION MANAGEMENT**: Track expiration dates and prioritize usage
        3. **AVAILABILITY CHECKS**: Verify ingredient availability for recipes
        4. **QUANTITY UPDATES**: Update inventory after recipe preparation
        5. **WASTE PREVENTION**: Alert about items expiring within 3 days
        6. **DATA SYNCHRONIZATION**: Maintain sync between cache and Google Sheets
        7. **REPORTING**: Provide inventory summaries and analytics
        8. **INTER-AGENT COMMUNICATION**: Share data with Executive Chef and Sous Chef

        ###MCP CLIENT CAPABILITIES###
        As an MCP (Model Context Protocol) client, you can:
        - **Read from Google Sheets**: Fetch current inventory data
        - **Write to Google Sheets**: Update quantities after consumption
        - **Query Specific Items**: Check availability of specific ingredients
        - **Batch Operations**: Process multiple inventory updates efficiently
        - **Data Validation**: Ensure data integrity and consistency

        ###GOOGLE SHEETS SCHEMA###
        Expected columns in inventory sheet:
        - **ingredient_name**: Name of the ingredient (e.g., "Chicken Breast")
        - **quantity**: Current quantity (numeric)
        - **unit**: Unit of measurement (e.g., "lb", "oz", "cup", "piece")
        - **expiration_date**: Expiration date (YYYY-MM-DD format)
        - **category**: Food category (e.g., "protein", "vegetable", "dairy")
        - **location**: Storage location (e.g., "fridge", "freezer", "pantry")
        - **last_updated**: Timestamp of last update

        ###COMMUNICATION PROTOCOLS###

        **With Executive Chef Agent**:
        - Receive: Requests for inventory summary, expiration alerts, feasibility checks
        - Send: Inventory status, expiring items list, ingredient availability reports

        **With Sous Chef Agent**:
        - Receive: Recipe ingredient requirements for feasibility checks
        - Send: Availability confirmations, quantity sufficiency status, substitution needs

        **Message Format**:
        {
            "from": "pantry_agent",
            "to": "target_agent",
            "action": "action_type",
            "data": {...},
            "timestamp": "ISO-8601",
            "priority": "high|medium|low"
        }

        ###OPERATIONS###

        **1. Check Inventory**
        - Query Google Sheets for all ingredients
        - Return structured inventory data
        - Update local cache

        **2. Check Expiring Items**
        - Filter items expiring within N days (default: 3)
        - Sort by expiration date (soonest first)
        - Calculate waste risk score

        **3. Check Recipe Feasibility**
        - Receive ingredient requirements from Sous Chef
        - Verify availability and sufficiency of each ingredient
        - Identify missing or insufficient items
        - Suggest substitutions if available

        **4. Update Inventory**
        - Receive consumption data after recipe preparation
        - Calculate new quantities
        - Write updates to Google Sheets
        - Log transaction history

        **5. Add New Ingredient**
        - Accept new ingredient data
        - Validate data format
        - Append to Google Sheets
        - Confirm addition

        **6. Get Pantry Summary**
        - Count total ingredients
        - Count expiring items
        - Calculate inventory health score
        - Identify low-stock items

        ###EXPIRATION PRIORITY SYSTEM###

        **Priority Levels**:
        - **CRITICAL** (0-1 days): Use immediately or discard
        - **HIGH** (2-3 days): Prioritize in next meal
        - **MEDIUM** (4-7 days): Plan to use this week
        - **LOW** (8+ days): Monitor regularly

        **Waste Prevention Strategy**:
        1. Alert Executive Chef about critical/high priority items
        2. Request Sous Chef to suggest recipes using expiring ingredients
        3. Proactively suggest meal plans to reduce waste
        4. Track waste metrics and report trends

        ###QUANTITY MANAGEMENT###

        **Sufficiency Rules**:
        - Check if quantity >= required amount
        - Consider partial availability (e.g., 0.8x required)
        - Flag items below reorder threshold
        - Suggest shopping list for missing items

        **Unit Conversions**:
        - Support common conversions (lb to oz, cup to ml, etc.)
        - Handle fractional quantities
        - Standardize units for consistency

        ###ERROR HANDLING###

        **MCP Connection Failures**:
        - Fall back to local cache if available
        - Log error and notify Executive Chef
        - Retry with exponential backoff
        - Provide degraded service mode

        **Data Inconsistencies**:
        - Validate data types and ranges
        - Handle missing or malformed data
        - Apply default values when appropriate
        - Alert about data quality issues

        **Sync Conflicts**:
        - Timestamp-based conflict resolution
        - Prefer Google Sheets as source of truth
        - Log conflicts for manual review

        ###INSTRUCTIONS###
        1. **INITIALIZE**: Connect to Google Sheets MCP on startup
        2. **SYNC**: Fetch initial inventory data and cache locally
        3. **MONITOR**: Continuously check for expiring items
        4. **RESPOND**: Process requests from Executive Chef and Sous Chef
        5. **UPDATE**: Reflect recipe consumption in Google Sheets
        6. **ALERT**: Proactively notify about expiring items
        7. **OPTIMIZE**: Suggest ingredient usage to minimize waste
        8. **LOG**: Maintain audit trail of all operations

        ###CHAIN OF THOUGHTS###
        1. **RECEIVE**: What request am I getting? (check, update, alert, report)
        2. **VALIDATE**: Is the request properly formatted and authorized?
        3. **CACHE CHECK**: Can I serve from cache or need fresh data?
        4. **MCP QUERY**: What Google Sheets operation do I need?
        5. **PROCESS**: Transform data into requested format
        6. **VALIDATE OUTPUT**: Is the response complete and accurate?
        7. **UPDATE CACHE**: Should I update local cache?
        8. **LOG**: Record operation for audit trail
        9. **RESPOND**: Send formatted response to requesting agent
        10. **PROACTIVE**: Any alerts or suggestions to send?

        ###WHAT NOT TO DO###
        - DO NOT SUGGEST RECIPES — That's the Sous Chef's role
        - DO NOT MAKE DECISIONS ABOUT MEAL PLANNING — That's the Executive Chef's role
        - DO NOT MODIFY INVENTORY WITHOUT AUTHORIZATION — Always log changes
        - DO NOT IGNORE EXPIRATION DATES — Waste prevention is critical
        - DO NOT SERVE STALE CACHE DATA — Sync regularly with Google Sheets
        - DO NOT EXPOSE RAW MCP ERRORS TO USERS — Handle gracefully
        - DO NOT ASSUME INGREDIENT AVAILABILITY — Always verify

        ###EXAMPLE SCENARIOS###

        **Scenario 1: Inventory Check Request**
        Executive Chef: "Show me current inventory"
        Pantry Agent:
        1. Query Google Sheets via MCP
        2. Parse response into structured format
        3. Update local cache
        4. Return inventory list with quantities and expiration dates

        **Scenario 2: Expiring Items Alert**
        (Proactive check runs every hour)
        Pantry Agent detects milk expires tomorrow:
        1. Flag milk as HIGH priority
        2. Send alert to Executive Chef
        3. Suggest: "Milk expires tomorrow (1 quart). Consider using in recipe."

        **Scenario 3: Recipe Feasibility Check**
        Sous Chef: "Can we make carbonara? Need: pasta, eggs, bacon, parmesan"
        Pantry Agent:
        1. Query inventory for each ingredient
        2. Check quantities:
           - Pasta: ✅ 2 lb available (need 1 lb)
           - Eggs: ✅ 6 available (need 4)
           - Bacon: ❌ Not available
           - Parmesan: ⚠️  2 oz available (need 4 oz - partial)
        3. Respond: "Partially feasible. Missing: bacon. Insufficient: parmesan (have 2oz, need 4oz)"
        4. Suggest: "Consider pancetta as bacon substitute"

        **Scenario 4: Post-Recipe Inventory Update**
        Executive Chef: "Update inventory after making pasta. Used: pasta (1 lb), tomatoes (3), olive oil (2 tbsp)"
        Pantry Agent:
        1. Fetch current quantities from Google Sheets
        2. Calculate new quantities:
           - Pasta: 2 lb → 1 lb
           - Tomatoes: 8 → 5
           - Olive Oil: 16 oz → 15 oz
        3. Update Google Sheets via MCP
        4. Confirm: "Inventory updated successfully"
        5. Check for low stock: "Note: Pasta now at 1 lb - consider restocking"

        **Scenario 5: Shopping List Generation**
        Executive Chef: "What do we need to buy?"
        Pantry Agent:
        1. Identify items below reorder threshold
        2. Check expiring items (don't repurchase)
        3. Generate shopping list:
           - Bacon: 0 lb (need 1 lb)
           - Parmesan: 2 oz (recommend 8 oz)
           - Bread: 0 loaves (need 1)
        4. Provide list with priorities and suggested quantities

        ###OPTIMIZATION PRINCIPLES###
        1. **Cache Intelligently**: Balance freshness vs. performance
        2. **Batch Operations**: Group MCP requests when possible
        3. **Proactive Alerts**: Don't wait to be asked about expiring items
        4. **Data Integrity**: Validate all inputs and outputs
        5. **Graceful Degradation**: Provide partial service if MCP unavailable
        6. **Waste Awareness**: Always prioritize expiring items
        7. **Communication**: Clear, structured responses to other agents

        ###METRICS TO TRACK###
        - Total inventory value
        - Waste rate (items expired unused)
        - Turnover rate (how quickly items are used)
        - Low-stock incidents
        - MCP sync success rate
        - Response time to queries

        </system_prompt>
        """

    def log_operation(self, operation: str, details: Dict[str, Any]):
        """Log an operation for audit trail."""
        self.operation_log.append({
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'details': details,
            'agent': self.name
        })

    # ============================================
    # MCP INTEGRATION METHODS
    # ============================================

    def connect_mcp(self, mcp_client) -> bool:
        """
        Connect to Google Sheets MCP client.

        Args:
            mcp_client: MCP client instance for Google Sheets

        Returns:
            bool: Connection success status
        """
        try:
            self.mcp_client = mcp_client
            self.log_operation('mcp_connect', {'status': 'success'})
            print(f"🔗 {self.name}: Connected to Google Sheets MCP")
            return True
        except Exception as e:
            self.log_operation('mcp_connect', {'status': 'failed', 'error': str(e)})
            print(f"❌ {self.name}: MCP connection failed - {str(e)}")
            return False

    async def fetch_inventory_from_sheets(self, spreadsheet_id: str, range_name: str = "Inventory!A2:G") -> List[Dict[str, Any]]:
        """
        Fetch inventory data from Google Sheets via MCP.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            range_name: Range to fetch (default: Inventory sheet, rows starting at 2)

        Returns:
            List of inventory items as dictionaries
        """
        if not self.mcp_client:
            print(f"⚠️  {self.name}: No MCP client connected, using cached data")
            return list(self.inventory_cache.values())

        try:
            # Use MCP client to read from Google Sheets
            # Format: [ingredient_name, quantity, unit, expiration_date, category, location, last_updated]
            response = await self.mcp_client.read_resource(f"sheets://{spreadsheet_id}/{range_name}")

            rows = response.get('values', [])
            inventory_items = []

            for row in rows:
                if len(row) >= 4:  # Minimum required fields
                    item = {
                        'ingredient_name': row[0],
                        'quantity': float(row[1]) if row[1] else 0.0,
                        'unit': row[2] if len(row) > 2 else '',
                        'expiration_date': row[3] if len(row) > 3 else None,
                        'category': row[4] if len(row) > 4 else 'other',
                        'location': row[5] if len(row) > 5 else 'pantry',
                        'last_updated': row[6] if len(row) > 6 else datetime.now().isoformat()
                    }
                    inventory_items.append(item)

                    # Update cache
                    self.inventory_cache[self._normalize_name(item['ingredient_name'])] = item

            self.last_sync = datetime.now()
            self.log_operation('fetch_inventory', {
                'status': 'success',
                'items_count': len(inventory_items),
                'spreadsheet_id': spreadsheet_id
            })

            print(f"✅ {self.name}: Fetched {len(inventory_items)} items from Google Sheets")
            return inventory_items

        except Exception as e:
            self.log_operation('fetch_inventory', {
                'status': 'failed',
                'error': str(e),
                'spreadsheet_id': spreadsheet_id
            })
            print(f"❌ {self.name}: Failed to fetch from Google Sheets - {str(e)}")
            # Fall back to cache
            return list(self.inventory_cache.values())

    async def update_inventory_in_sheets(
        self,
        spreadsheet_id: str,
        updates: List[Dict[str, Any]],
        range_name: str = "Inventory!A2:G"
    ) -> bool:
        """
        Update inventory quantities in Google Sheets via MCP.

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            updates: List of updates with format:
                     [{'ingredient_name': str, 'quantity': float, 'unit': str, ...}]
            range_name: Range to update

        Returns:
            bool: Update success status
        """
        if not self.mcp_client:
            print(f"⚠️  {self.name}: No MCP client connected, updates cached locally")
            return False

        try:
            # Prepare batch update data
            update_values = []
            for update in updates:
                row = [
                    update.get('ingredient_name', ''),
                    update.get('quantity', 0),
                    update.get('unit', ''),
                    update.get('expiration_date', ''),
                    update.get('category', 'other'),
                    update.get('location', 'pantry'),
                    datetime.now().isoformat()
                ]
                update_values.append(row)

            # Use MCP client to write to Google Sheets
            await self.mcp_client.write_resource(
                f"sheets://{spreadsheet_id}/{range_name}",
                {'values': update_values}
            )

            # Update cache
            for update in updates:
                name = update.get('ingredient_name')
                if name:
                    self.add_or_update_ingredient(
                        ingredient_name=name,
                        quantity=update.get('quantity', 0),
                        unit=update.get('unit', ''),
                        expiration_date=update.get('expiration_date'),
                        category=update.get('category', 'other'),
                        location=update.get('location', 'pantry')
                    )

            self.log_operation('update_inventory', {
                'status': 'success',
                'updates_count': len(updates),
                'spreadsheet_id': spreadsheet_id
            })

            print(f"✅ {self.name}: Updated {len(updates)} items in Google Sheets")
            return True

        except Exception as e:
            self.log_operation('update_inventory', {
                'status': 'failed',
                'error': str(e),
                'spreadsheet_id': spreadsheet_id
            })
            print(f"❌ {self.name}: Failed to update Google Sheets - {str(e)}")
            return False

    # ============================================
    # INVENTORY QUERY METHODS
    # ============================================

    def get_inventory(self) -> List[Dict[str, Any]]:
        """
        Get current inventory from cache.

        Returns:
            List of all inventory items
        """
        return list(self.inventory_cache.values())

    def get_ingredient(self, ingredient_name: str) -> Optional[Dict[str, Any]]:
        """
        Get specific ingredient details.

        Args:
            ingredient_name: Name of the ingredient

        Returns:
            Ingredient details or None if not found
        """
        normalized = self._normalize_name(ingredient_name)
        return self.inventory_cache.get(normalized) or self.inventory_cache.get(ingredient_name)

    def get_expiring_soon(self, days_threshold: int = 3) -> List[Dict[str, Any]]:
        """
        Get ingredients expiring within the specified number of days.

        Args:
            days_threshold: Number of days to check (default: 3)

        Returns:
            List of expiring items sorted by expiration date
        """
        expiring_items = []
        today = datetime.now().date()
        threshold_date = today + timedelta(days=days_threshold)

        for item in self.inventory_cache.values():
            exp_date_str = item.get('expiration_date')
            if exp_date_str:
                try:
                    # Parse expiration date - handle both date-only and datetime strings
                    if 'T' in exp_date_str or ' ' in exp_date_str:
                        exp_datetime = datetime.fromisoformat(exp_date_str.replace('Z', '+00:00'))
                        exp_date = exp_datetime.date()
                    else:
                        exp_date = datetime.fromisoformat(exp_date_str).date()

                    if exp_date <= threshold_date:
                        days_until_expiry = (exp_date - today).days
                        item_copy = item.copy()
                        item_copy['days_until_expiry'] = days_until_expiry

                        # Assign priority
                        if days_until_expiry < 2:
                            item_copy['priority'] = 'CRITICAL'
                        elif days_until_expiry <= 3:
                            item_copy['priority'] = 'HIGH'
                        elif days_until_expiry <= 7:
                            item_copy['priority'] = 'MEDIUM'
                        else:
                            item_copy['priority'] = 'LOW'

                        expiring_items.append(item_copy)
                except (ValueError, AttributeError):
                    continue

        # Sort by expiration date (soonest first)
        expiring_items.sort(key=lambda x: x['days_until_expiry'])

        self.log_operation('check_expiring', {
            'days_threshold': days_threshold,
            'items_found': len(expiring_items)
        })

        return expiring_items

    def get_pantry_summary(self) -> Dict[str, Any]:
        """
        Get high-level pantry statistics.

        Returns:
            Dictionary with pantry metrics
        """
        inventory = self.get_inventory()
        expiring = self.get_expiring_soon()

        # Count by category
        categories = {}
        for item in inventory:
            cat = item.get('category', 'other')
            categories[cat] = categories.get(cat, 0) + 1

        # Count by location
        locations = {}
        for item in inventory:
            loc = item.get('location', 'pantry')
            locations[loc] = locations.get(loc, 0) + 1

        summary = {
            'total_ingredients': len(inventory),
            'expiring_soon': len(expiring),
            'critical_items': len([x for x in expiring if x.get('priority') == 'CRITICAL']),
            'high_priority_items': len([x for x in expiring if x.get('priority') == 'HIGH']),
            'categories': categories,
            'locations': locations,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'cache_status': 'active' if self.inventory_cache else 'empty'
        }

        return summary

    # ============================================
    # RECIPE FEASIBILITY METHODS
    # ============================================

    def check_recipe_feasibility(
        self,
        required_ingredients: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check if a recipe can be made with current inventory.

        Args:
            required_ingredients: List of required ingredients
                Format: [{'name': str, 'quantity': float, 'unit': str}, ...]

        Returns:
            Dictionary with feasibility status and details
        """
        available = []
        insufficient = []
        missing = []

        for req in required_ingredients:
            req_name = req['name']
            req_quantity = req['quantity']
            req_unit = req['unit']

            inv_item = self.get_ingredient(req_name)

            if not inv_item:
                missing.append({
                    'ingredient': req_name,
                    'required': f"{req_quantity} {req_unit}",
                    'available': "0"
                })
            else:
                inv_quantity = inv_item['quantity']
                inv_unit = inv_item['unit']

                # Simple unit matching (in production, would need unit conversion)
                if inv_unit == req_unit:
                    if inv_quantity >= req_quantity:
                        available.append({
                            'ingredient': req_name,
                            'required': f"{req_quantity} {req_unit}",
                            'available': f"{inv_quantity} {inv_unit}",
                            'status': 'sufficient'
                        })
                    else:
                        insufficient.append({
                            'ingredient': req_name,
                            'required': f"{req_quantity} {req_unit}",
                            'available': f"{inv_quantity} {inv_unit}",
                            'shortage': f"{req_quantity - inv_quantity} {req_unit}"
                        })
                else:
                    # Different units - flag for manual review
                    insufficient.append({
                        'ingredient': req_name,
                        'required': f"{req_quantity} {req_unit}",
                        'available': f"{inv_quantity} {inv_unit}",
                        'note': 'Unit conversion required'
                    })

        feasible = len(missing) == 0 and len(insufficient) == 0
        partially_feasible = len(missing) < len(required_ingredients)

        result = {
            'feasible': feasible,
            'partially_feasible': partially_feasible,
            'available_ingredients': available,
            'insufficient_ingredients': insufficient,
            'missing_ingredients': missing,
            'completion_percentage': (len(available) / len(required_ingredients) * 100) if required_ingredients else 0
        }

        self.log_operation('check_feasibility', {
            'required_count': len(required_ingredients),
            'feasible': feasible,
            'completion': result['completion_percentage']
        })

        return result

    def suggest_substitutions(
        self,
        missing_ingredients: List[str],
        llm
    ) -> Dict[str, List[str]]:
        """
        Suggest substitutions for missing ingredients based on available inventory.

        Args:
            missing_ingredients: List of missing ingredient names
            llm: Language model for intelligent suggestions

        Returns:
            Dictionary mapping missing ingredients to available substitutes
        """
        system_prompt = self.build_system_prompt()
        available_items = [item['ingredient_name'] for item in self.get_inventory()]

        substitution_instruction = f"""
        Suggest substitutions for missing ingredients based on available inventory.

        Missing ingredients: {', '.join(missing_ingredients)}
        Available ingredients: {', '.join(available_items)}

        Return ONLY valid JSON:
        {{
            "substitutions": {{
                "missing_ingredient": ["substitute1", "substitute2"],
                ...
            }},
            "notes": "Any important notes about substitutions"
        }}
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=substitution_instruction)
        ]

        try:
            response = llm.invoke(messages)
            result = json.loads(response.content)
            return result.get('substitutions', {})
        except:
            return {}

    # ============================================
    # INVENTORY UPDATE METHODS
    # ============================================

    def consume_ingredients(
        self,
        consumption: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update inventory after recipe preparation (local cache only).
        Call update_inventory_in_sheets() to sync with Google Sheets.

        Args:
            consumption: List of consumed ingredients
                Format: [{'name': str, 'quantity': float, 'unit': str}, ...]

        Returns:
            Dictionary with update status
        """
        updates = []
        errors = []

        for item in consumption:
            name = item['name']
            consumed_qty = item['quantity']
            unit = item['unit']

            normalized_name = self._normalize_name(name)
            inv_item = self.inventory_cache.get(normalized_name)

            if not inv_item:
                errors.append(f"Ingredient '{name}' not found in inventory")
                continue

            if inv_item['unit'] != unit:
                errors.append(f"Unit mismatch for '{name}': inventory has {inv_item['unit']}, consumption in {unit}")
                continue

            new_quantity = inv_item['quantity'] - consumed_qty

            if new_quantity < 0:
                errors.append(f"Insufficient '{name}': have {inv_item['quantity']}, tried to consume {consumed_qty}")
                new_quantity = 0  # Don't allow negative

            # Update cache
            inv_item['quantity'] = new_quantity
            inv_item['last_updated'] = datetime.now().isoformat()
            self.inventory_cache[normalized_name] = inv_item

            updates.append({
                'ingredient': name,
                'old_quantity': inv_item['quantity'] + consumed_qty,
                'consumed': consumed_qty,
                'new_quantity': new_quantity,
                'unit': unit
            })

        self.log_operation('consume_ingredients', {
            'updates_count': len(updates),
            'errors_count': len(errors)
        })

        return {
            'success': len(errors) == 0,
            'updates': updates,
            'errors': errors
        }

    # ============================================
    # INTER-AGENT COMMUNICATION METHODS
    # ============================================

    def create_message_to_agent(
        self,
        target_agent: Literal["executive_chef", "sous_chef", "quality_control"],
        action: str,
        data: Dict[str, Any],
        priority: Literal["high", "medium", "low"] = "medium"
    ) -> Dict[str, Any]:
        """
        Create a standardized message to send to another agent.

        Args:
            target_agent: Target agent identifier
            action: Action type (e.g., "inventory_alert", "feasibility_response")
            data: Message data payload
            priority: Message priority level

        Returns:
            Formatted message dictionary
        """
        message = {
            'from': 'pantry_agent',
            'to': target_agent,
            'action': action,
            'data': data,
            'timestamp': datetime.now().isoformat(),
            'priority': priority
        }

        self.log_operation('send_message', {
            'to': target_agent,
            'action': action,
            'priority': priority
        })

        return message

    def handle_request_from_agent(
        self,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle incoming request from another agent.

        Args:
            request: Request message from another agent
                Format: {'from': str, 'action': str, 'data': dict, ...}

        Returns:
            Response dictionary
        """
        from_agent = request.get('from', 'unknown')
        action = request.get('action', '')
        data = request.get('data', {})

        print(f"📥 {self.name}: Received '{action}' request from {from_agent}")

        # Route request to appropriate method
        if action == 'check_inventory':
            response_data = {
                'inventory': self.get_inventory(),
                'summary': self.get_pantry_summary()
            }

        elif action == 'check_expiring':
            days = data.get('days_threshold', 3)
            response_data = {
                'expiring_items': self.get_expiring_soon(days)
            }

        elif action == 'check_feasibility':
            required = data.get('required_ingredients', [])
            response_data = self.check_recipe_feasibility(required)

        elif action == 'consume_ingredients':
            consumption = data.get('consumption', [])
            response_data = self.consume_ingredients(consumption)

        elif action == 'get_summary':
            response_data = self.get_pantry_summary()

        else:
            response_data = {
                'error': f"Unknown action: {action}"
            }

        response = {
            'from': 'pantry_agent',
            'to': from_agent,
            'action': f"{action}_response",
            'data': response_data,
            'timestamp': datetime.now().isoformat(),
            'success': 'error' not in response_data
        }

        self.log_operation('handle_request', {
            'from': from_agent,
            'action': action,
            'success': response['success']
        })

        print(f"📤 {self.name}: Sent '{action}_response' to {from_agent}")

        return response

    # ============================================
    # PROACTIVE MONITORING METHODS
    # ============================================

    def generate_expiration_alerts(self) -> List[Dict[str, Any]]:
        """
        Generate alerts for expiring items (proactive monitoring).

        Returns:
            List of alert messages for other agents
        """
        expiring = self.get_expiring_soon(days_threshold=3)
        alerts = []

        if not expiring:
            return alerts

        # Create alert for Executive Chef
        critical = [x for x in expiring if x.get('priority') == 'CRITICAL']
        high = [x for x in expiring if x.get('priority') == 'HIGH']

        if critical or high:
            alert = self.create_message_to_agent(
                target_agent='executive_chef',
                action='expiration_alert',
                data={
                    'critical_items': critical,
                    'high_priority_items': high,
                    'message': f"{len(critical)} critical items and {len(high)} high-priority items expiring soon",
                    'recommendation': 'Suggest recipes using these ingredients to minimize waste'
                },
                priority='high' if critical else 'medium'
            )
            alerts.append(alert)

        self.log_operation('generate_alerts', {
            'alerts_count': len(alerts),
            'critical_items': len(critical),
            'high_priority_items': len(high)
        })

        return alerts

    def get_operation_log(self) -> List[Dict[str, Any]]:
        """Return the full operation log for debugging/monitoring."""
        return self.operation_log

    def clear_logs(self):
        """Clear operation logs (useful for testing or fresh start)."""
        self.operation_log = []
