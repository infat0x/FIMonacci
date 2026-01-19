package com.fimonacci.app.navigation

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import com.fimonacci.app.ui.screen.*
import com.fimonacci.app.ui.theme.*
import com.fimonacci.app.ui.viewmodel.DashboardViewModel

/**
 * Navigation Routes
 */
sealed class Screen(val route: String, val title: String, val icon: ImageVector) {
    object Dashboard : Screen("dashboard", "Dashboard", Icons.Outlined.Dashboard)
    object Alerts : Screen("alerts", "Alerts", Icons.Outlined.Notifications)
    object Agents : Screen("agents", "Agents", Icons.Outlined.Computer)
    object Settings : Screen("settings", "Settings", Icons.Outlined.Settings)

    object AlertDetail : Screen("alert_detail/{alertId}", "Alert Detail", Icons.Outlined.Notifications) {
        fun createRoute(alertId: Int) = "alert_detail/$alertId"
    }

    object AgentDetail : Screen("agent_detail/{agentId}", "Agent Detail", Icons.Outlined.Computer) {
        fun createRoute(agentId: Int) = "agent_detail/$agentId"
    }
}

/**
 * Bottom Navigation Items
 */
val bottomNavItems = listOf(
    Screen.Dashboard,
    Screen.Alerts,
    Screen.Agents,
    Screen.Settings
)

/**
 * Main App Scaffold with Bottom Navigation
 */
@Composable
fun AppScaffold(
    navController: NavHostController,
    viewModel: DashboardViewModel,
    settingsViewModel: com.fimonacci.app.ui.viewmodel.SettingsViewModel? = null
) {
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = navBackStackEntry?.destination

    // Determine if we should show bottom nav (hide on detail screens)
    val showBottomBar = currentDestination?.route !in listOf(
        Screen.AlertDetail.route,
        Screen.AgentDetail.route
    )

    Scaffold(
        containerColor = GitHubBackground,
        bottomBar = {
            if (showBottomBar) {
                NavigationBar(
                    containerColor = GitHubSurface,
                    tonalElevation = 8.dp
                ) {
                    bottomNavItems.forEach { screen ->
                        val selected = currentDestination?.hierarchy?.any {
                            it.route == screen.route
                        } == true

                        NavigationBarItem(
                            icon = {
                                Icon(
                                    imageVector = screen.icon,
                                    contentDescription = screen.title
                                )
                            },
                            label = {
                                Text(
                                    text = screen.title,
                                    style = MaterialTheme.typography.labelSmall
                                )
                            },
                            selected = selected,
                            onClick = {
                                navController.navigate(screen.route) {
                                    // Pop up to the start destination of the graph to
                                    // avoid building up a large stack of destinations
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    // Avoid multiple copies of the same destination
                                    launchSingleTop = true
                                    // Restore state when reselecting a previously selected item
                                    restoreState = true
                                }
                            },
                            colors = NavigationBarItemDefaults.colors(
                                selectedIconColor = PrimaryAccent,
                                selectedTextColor = PrimaryAccent,
                                unselectedIconColor = GitHubTextSecondary,
                                unselectedTextColor = GitHubTextSecondary,
                                indicatorColor = androidx.compose.ui.graphics.Color.Transparent
                            )
                        )
                    }
                }
            }
        }
    ) { paddingValues ->
        AppNavGraph(
            navController = navController,
            viewModel = viewModel,
            settingsViewModel = settingsViewModel,
            modifier = Modifier.padding(paddingValues)
        )
    }
}

/**
 * Navigation Graph
 */
@Composable
fun AppNavGraph(
    navController: NavHostController,
    viewModel: DashboardViewModel,
    settingsViewModel: com.fimonacci.app.ui.viewmodel.SettingsViewModel? = null,
    modifier: Modifier = Modifier
) {
    // Observe state to ensure UI updates when data changes
    val uiState by viewModel.uiState.collectAsState()
    val alerts = uiState.alerts
    val agents = uiState.agents
    val isLoading = uiState.isLoading
    
    // Auto-refresh when real-time is connected and state changes
    LaunchedEffect(uiState.realTimeConnected) {
        if (uiState.realTimeConnected) {
            // Real-time is active, data will update via WebSocket
        }
    }

    NavHost(
        navController = navController,
        startDestination = Screen.Dashboard.route,
        modifier = modifier
    ) {
        // Dashboard Screen
        composable(Screen.Dashboard.route) {
            DashboardScreen(
                onAlertClick = { alert ->
                    val alertIndex = alerts.indexOfFirst { it.id == alert.id }
                    if (alertIndex >= 0) {
                        navController.navigate(Screen.AlertDetail.createRoute(alertIndex))
                    }
                },
                viewModel = viewModel
            )
        }

        // Alerts List Screen
        composable(Screen.Alerts.route) {
            AlertsScreen(
                alerts = alerts,
                isLoading = isLoading,
                onAlertClick = { alert ->
                    val alertIndex = alerts.indexOfFirst { it.id == alert.id }
                    if (alertIndex >= 0) {
                        navController.navigate(Screen.AlertDetail.createRoute(alertIndex))
                    }
                },
                onRefresh = { viewModel.refreshAlerts() }
            )
        }

        // Agents Screen
        composable(Screen.Agents.route) {
            AgentsScreen(
                agents = agents,
                isLoading = isLoading,
                onAgentClick = { agent ->
                    navController.navigate(Screen.AgentDetail.createRoute(agent.id))
                }
            )
        }

        // Settings Screen
        composable(Screen.Settings.route) {
            SettingsScreen(
                onRefreshTriggered = { viewModel.refresh() },
                actualViewModel = settingsViewModel
            )
        }

        // Alert Detail Screen
        composable(Screen.AlertDetail.route) { backStackEntry ->
            val alertId = backStackEntry.arguments?.getString("alertId")?.toIntOrNull()
            val alert = alertId?.let { if (it in alerts.indices) alerts[it] else null }

            if (alert != null) {
                AlertDetailScreen(
                    alert = alert,
                    onBackClick = { navController.popBackStack() }
                )
            } else {
                // Navigate back if alert not found
                LaunchedEffect(Unit) {
                    navController.popBackStack()
                }
            }
        }

        // Agent Detail Screen
        composable(Screen.AgentDetail.route) { backStackEntry ->
            val agentId = backStackEntry.arguments?.getString("agentId")?.toIntOrNull()

            if (agentId != null) {
                AgentDetailScreen(
                    agentId = agentId,
                    onBackClick = { navController.popBackStack() }
                )
            } else {
                // Navigate back if agent ID not found
                LaunchedEffect(Unit) {
                    navController.popBackStack()
                }
            }
        }
    }
}
